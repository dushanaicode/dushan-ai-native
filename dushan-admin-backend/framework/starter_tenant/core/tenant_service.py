import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.spi.tenant_access_provider import TenantAccessProvider
from framework.starter_tenant.config.tenant_settings import TenantSettings
from framework.starter_tenant.context.tenant_context import TenantContext
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.tenant_access_grant import TenantAccessGrant
from framework.starter_tenant.model.tenant_info import TenantInfo
from framework.starter_tenant.model.tenant_provisioning_result import TenantProvisioningResult


@framework(scope=ComponentScopeEnum.SINGLETON)
class TenantService(TenantAccessProvider):
    """租户准入、部署状态及开户接点；业务目录与可信身份仍由相应 SPI 提供。"""

    def __init__(
        self,
        settings: TenantSettings,
        context: TenantContext,
        security: SecurityContext,
        database: SessionProvider,
    ):
        self.settings = settings.model_copy(deep=True)
        self.context, self.security, self.database = context, security, database
        self.directory = None
        self.provisioning = None
        self.ready = False

    def supports(self, capability: str) -> bool:
        return (
            self.ready and self.directory is not None and capability in self.settings.capabilities()
        )

    def _require_ready(self):
        if not self.ready or self.directory is None:
            raise TenantException("configuration")

    async def _call(self, callback):
        try:
            async with asyncio.timeout(self.settings.provider_timeout_seconds):
                return await callback()
        except TenantException:
            raise
        except BaseBusinessException as error:
            if 400 <= error.http_status < 500:
                raise
            raise TenantException("configuration", cause=error) from error
        except Exception as error:
            raise TenantException("configuration", cause=error) from error

    async def _tenant(self, tenant_id):
        result = await self._call(lambda: self.directory.get_tenant(tenant_id))
        if result is not None and (
            not isinstance(result, TenantInfo) or result.tenant_id != tenant_id
        ):
            raise TenantException("configuration")
        return result

    def _target(self, identity):
        target = identity.tenant_id if self.settings.enabled else self.settings.default_tenant_id
        if target is None:
            raise TenantException("missing")
        if identity.tenant_id != target:
            raise TenantException("denied")
        return target

    @asynccontextmanager
    async def enter(self, identity, policy):
        self._require_ready()
        if self.security.current() is not identity:
            raise TenantException("denied")
        target = self._target(identity)
        info = await self._tenant(target)
        if info is None:
            raise TenantException("unknown")
        if not info.enabled:
            raise TenantException("disabled")
        if identity.access_mode is TenantAccessMode.GROUP_MANAGED and not self.supports(
            "group_managed_access"
        ):
            raise TenantException("denied")
        if policy.required_capability is not None and not self.supports(policy.required_capability):
            raise TenantException("denied")
        grant = await self._call(lambda: self.directory.authorize_session(identity, policy))
        seconds = min(
            self.settings.execution_seconds,
            (identity.expires_at - datetime.now(UTC)).total_seconds(),
        )
        resources = None
        if identity.realm is SecurityRealm.SUPPORT:
            if (
                not isinstance(grant, TenantAccessGrant)
                or grant.tenant_id != target
                or not grant.resources
                or any(rule.actions != frozenset({"select"}) for rule in grant.resources)
            ):
                raise TenantException("denied")
            resources = grant.resources
            seconds = min(seconds, (grant.expires_at - datetime.now(UTC)).total_seconds())
        elif grant is not None:
            raise TenantException("configuration")
        if seconds <= 0:
            raise TenantException("expired")
        with self.context._bind(target, identity, seconds=seconds, resources=resources):
            yield

    @asynccontextmanager
    async def enter_workload(self, identity, capability):
        self._require_ready()
        if (
            self.security.current_workload() is not identity
            or capability not in identity.capabilities
        ):
            raise TenantException("denied")
        target = self._target(identity)
        grant = await self._call(lambda: self.directory.authorize_workload(identity, capability))
        if not isinstance(grant, TenantAccessGrant) or grant.tenant_id != target:
            raise TenantException("denied")
        info = await self._tenant(target)
        available = info is not None and info.enabled
        if not available and not grant.allow_unavailable:
            raise TenantException("unknown" if info is None else "disabled")
        seconds = min(
            self.settings.execution_seconds,
            (identity.expires_at - datetime.now(UTC)).total_seconds(),
            (grant.expires_at - datetime.now(UTC)).total_seconds(),
        )
        if seconds <= 0:
            raise TenantException("expired")
        with self.context._bind(
            target, identity, seconds=seconds, resources=grant.resources, available=available
        ):
            yield

    def require_enabled(self):
        if not self.context.current().available:
            raise TenantException("disabled")

    def require_target(self, target: str):
        """客户端目标只用于一致性检查，不作为授权来源。"""
        if target != self.context.get_required_tenant_id():
            raise TenantException("denied")

    async def targets(self):
        self._require_ready()
        values = await self._call(self.directory.enabled_tenant_ids)
        if (
            not isinstance(values, tuple)
            or any(not isinstance(item, str) or not item for item in values)
            or len(set(values)) != len(values)
        ):
            raise TenantException("configuration")
        if not self.settings.enabled:
            return (
                (self.settings.default_tenant_id,)
                if self.settings.default_tenant_id in values
                else ()
            )
        return values

    async def target_batches(self):
        values = await self.targets()
        for offset in range(0, len(values), self.settings.target_batch_size):
            yield values[offset : offset + self.settings.target_batch_size]

    async def provision_authenticated(self, request):
        self._require_ready()
        identity = self.security.current()
        if (
            not isinstance(identity, LoginSession)
            or identity.realm is not SecurityRealm.ACCOUNT
            or self.provisioning is None
        ):
            raise TenantException("denied")
        if self.settings.enabled and not self.supports("self_service_provisioning"):
            raise TenantException("denied")
        async with self.database.transaction():
            fixed = None if self.settings.enabled else self.settings.default_tenant_id
            result = await self._call(
                lambda: self.provisioning.provision(identity, request, fixed_tenant_id=fixed)
            )
            if (
                not isinstance(result, TenantProvisioningResult)
                or fixed is not None
                and result.tenant_id != fixed
            ):
                raise TenantException("configuration")
            info = await self._tenant(result.tenant_id)
            if info is None or not info.enabled:
                raise TenantException("configuration")
        return result

    async def close(self):
        self.ready = False
        await self.context.close()
