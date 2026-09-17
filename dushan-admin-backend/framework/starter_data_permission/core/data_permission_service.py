import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from contextvars import ContextVar
from time import monotonic

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_data_permission.config.data_permission_settings import DataPermissionSettings
from framework.starter_data_permission.core.data_scope_resolver import DataScopeResolver
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_data_permission.model.data_exemption import DataExemption
from framework.starter_data_permission.model.data_grant import DataGrant
from framework.starter_data_permission.model.data_permission_frame import DataPermissionFrame
from framework.starter_data_permission.model.data_permission_snapshot import DataPermissionSnapshot
from framework.starter_data_permission.spi.data_exemption_provider import DataExemptionProvider
from framework.starter_data_permission.spi.data_permission_provider import DataPermissionProvider
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.conditional import conditional
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.spi.data_access_provider import DataAccessProvider


@framework(scope=ComponentScopeEnum.SINGLETON)
@conditional(lambda config: config.get_config(DataPermissionSettings).enabled)
class DataPermissionService(DataAccessProvider):
    """执行内固定快照；跨执行只按权威授权版本复用 Cache。

    撤销首先由 Security 实时会话解析阻止新执行；已有执行在退出或快照到期时
    失效，显式 invalidate 还会使当前执行失效。过期不在分页中途刷新。
    """

    def __init__(
        self,
        settings: DataPermissionSettings,
        security: SecurityContext,
        provider: DataPermissionProvider,
        cache: CacheHandler,
    ):
        self.settings = settings.model_copy(deep=True)
        self.security = security
        self.cache = cache
        self.resolver = DataScopeResolver(provider)
        self.exemptions: DataExemptionProvider | None = None
        self._frame = ContextVar(f"data_permission_{id(self)}", default=None)
        self._exemptions = ContextVar(f"data_exemptions_{id(self)}", default=())
        self._closed = False
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()

    async def _call(self, callback):
        try:
            async with asyncio.timeout(self.settings.provider_timeout_seconds):
                return await callback()
        except DataPermissionException:
            raise
        except Exception as error:
            raise DataPermissionException("provider", cause=error) from error

    def _identifier(self, identity):
        parts = [
            SecurityService.binding(identity),
            identity.dept_id,
            identity.authorization_revision,
            self.settings.rule_version,
        ]
        return hashlib.sha256(json.dumps(parts, separators=(",", ":")).encode()).hexdigest()

    async def _load(self, identity):
        binding = self._identifier(identity)

        async def load():
            grant = await self.resolver.resolve(identity)
            if identity.access_mode is TenantAccessMode.DIRECT_MEMBERSHIP:
                revision = await self.resolver.provider.revision(identity)
                if not isinstance(revision, str):
                    raise DataPermissionException("configuration")
                if revision != identity.authorization_revision:
                    raise DataPermissionException("stale")
            return DataPermissionSnapshot(
                binding=binding, revision=identity.authorization_revision, grant=grant
            ).model_dump(mode="json")

        if self.settings.cache_enabled:
            value = await self._call(
                lambda: self.cache.get_or_load(
                    self.settings.cache_key(),
                    binding,
                    load,
                    self.settings.cache_ttl_seconds,
                    wait_seconds=self.settings.provider_timeout_seconds,
                    critical_section_timeout_seconds=self.settings.provider_timeout_seconds,
                    lease_seconds=self.settings.provider_timeout_seconds + 1,
                )
            )
        else:
            value = await self._call(load)
        try:
            snapshot = DataPermissionSnapshot.model_validate_json(json.dumps(value))
        except (ValueError, TypeError) as error:
            raise DataPermissionException("provider", cause=error) from error
        if snapshot.binding != binding or snapshot.revision != identity.authorization_revision:
            raise DataPermissionException("provider")
        return snapshot.grant

    @asynccontextmanager
    async def enter(self, identity):
        if self._closed:
            raise DataPermissionException("closed")
        binding = ApplicationContext.current_execution()
        if binding.application is not self.security.application:
            raise DataPermissionException("configuration")
        current = (
            self.security.current()
            if isinstance(identity, LoginSession)
            else self.security.current_workload()
        )
        if current is not identity:
            raise DataPermissionException("missing")
        self._active += 1
        self._idle.clear()
        token = self._frame.set(None)
        frame = None
        try:
            grant = (
                await self._load(identity) if isinstance(identity, LoginSession) else DataGrant()
            )
            frame = DataPermissionFrame(
                binding, identity, grant, monotonic() + self.settings.snapshot_seconds
            )
            self._frame.set(frame)
            yield
        finally:
            if frame is not None:
                frame.active = False
            self._frame.reset(token)
            self._active -= 1
            if not self._active:
                self._idle.set()

    def current(self) -> DataPermissionFrame:
        frame = self._frame.get()
        if frame is None or not frame.active or not frame.binding.active:
            raise DataPermissionException("missing")
        if (
            frame.binding is not ApplicationContext.current_execution()
            or frame.binding.application is not self.security.application
        ):
            raise DataPermissionException("missing")
        current = (
            self.security.current()
            if isinstance(frame.identity, LoginSession)
            else self.security.current_workload()
        )
        if current is not frame.identity:
            raise DataPermissionException("missing")
        if monotonic() >= frame.expires_at:
            raise DataPermissionException("stale")
        return frame

    def require_membership_access(self, membership_id: str) -> str:
        frame = self.current()
        if frame.identity.tenant_id is None or not (
            frame.grant.tenant_all or membership_id in frame.grant.membership_ids
        ):
            raise DataPermissionException("denied")
        return frame.identity.tenant_id

    def require_tenant_all_access(self) -> str:
        frame = self.current()
        if frame.identity.tenant_id is None or not frame.grant.tenant_all:
            raise DataPermissionException("denied")
        return frame.identity.tenant_id

    async def invalidate(self, identity: LoginSession) -> None:
        """权限更新后失效旧版本；其他执行仍遵循固定快照的有效期上限。"""
        self.current()
        if identity.application_id != self.current().identity.application_id:
            raise DataPermissionException("denied")
        if self.settings.cache_enabled:
            await self._call(
                lambda: self.cache.delete(self.settings.cache_key(), self._identifier(identity))
            )
        frame = self._frame.get()
        if isinstance(frame.identity, LoginSession) and self._identifier(
            frame.identity
        ) == self._identifier(identity):
            frame.active = False

    @asynccontextmanager
    async def exempt(self, resource, operation, *, reason):
        frame = self.current()
        if (
            not resource
            or operation not in {"select", "insert", "update", "delete"}
            or not isinstance(reason, str)
            or not reason.strip()
            or len(reason) > 256
        ):
            raise DataPermissionException("configuration")
        if self.exemptions is None or frame.identity.tenant_id is None:
            raise DataPermissionException("denied")
        allowed = await self._call(
            lambda: self.exemptions.authorize(frame.identity, resource, operation, reason)
        )
        if allowed is not True:
            raise DataPermissionException("denied")
        self.current()
        exemption = DataExemption(frame, resource, operation)
        token = self._exemptions.set((*self._exemptions.get(), exemption))
        try:
            yield
        finally:
            exemption.active = False
            self._exemptions.reset(token)

    def is_exempt(self, resource, operation):
        frame = self.current()
        return any(
            item.active
            and item.frame is frame
            and item.resource == resource
            and item.operation == operation
            for item in self._exemptions.get()
        )

    def execution_key(self):
        if self._frame.get() is None:
            identity = self.security.current() or self.security.current_workload()
            if identity is None:
                raise DataPermissionException("missing")
            return identity
        frame = self.current()
        return frame, tuple(
            id(item) for item in self._exemptions.get() if item.active and item.frame is frame
        )

    async def close(self):
        self._closed = True
        await self._idle.wait()
