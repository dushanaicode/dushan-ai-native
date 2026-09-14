import asyncio
import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from contextvars import Context
from datetime import datetime, timezone

from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.conditional import conditional
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.core.permission_policy import PermissionPolicy
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_security.model.request_audit import RequestAudit
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.model.workload_message import WorkloadMessage
from framework.starter_security.spi.message_security_provider import MessageSecurityProvider
from framework.starter_security.spi.permission_provider import PermissionProvider
from framework.starter_security.spi.tenant_access_provider import TenantAccessProvider
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_security.spi.workload_provider import WorkloadProvider
from framework.starter_web.routing.route_policy import RoutePolicy


@framework(scope=ComponentScopeEnum.SINGLETON)
@conditional(lambda config: config.get_config(SecuritySettings).enabled)
class SecurityService:
    """本站会话验证与访问控制，不签发第三方令牌，不拥有 Cache/数据库资源。

    HTTP 使用 authorized；独立任务和消息用 run/run_message 创建新的 DI 边界。
    TokenProvider 的实时状态查询不可缓存，权限快照只按其权威版本复用。
    相邻模块通过 open 的显式 SPI 接入；缺失 Tenant/MQ 适配明确拒绝。
    """

    def __init__(
        self,
        settings: SecuritySettings,
        tokens: TokenProvider,
        permissions: PermissionProvider,
        cache: CacheHandler,
        context: SecurityContext,
    ):
        self.settings = settings.model_copy(deep=True)
        self.tokens = tokens
        self.permissions = permissions
        self.cache = cache
        self.context = context
        self._tenant: TenantAccessProvider | None = None
        self._messages: MessageSecurityProvider | None = None
        self._workloads: WorkloadProvider | None = None
        self._phase = "new"
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._close_task: asyncio.Task | None = None

    async def open(
        self,
        *,
        tenant: TenantAccessProvider | None = None,
        messages: MessageSecurityProvider | None = None,
        workloads: WorkloadProvider | None = None,
    ):
        if self._phase != "new" or not self.settings.enabled:
            raise SecurityException("closed")
        self._phase = "starting"
        self._tenant, self._messages = tenant, messages
        self._workloads = workloads
        if self.settings.permission_cache_enabled:
            await self._call(
                lambda: self.cache.eval_atomic(self.settings.cache_key(), ("probe",), "return 1")
            )
        self._phase = "ready"

    @asynccontextmanager
    async def _operation(self):
        if self._phase != "ready":
            raise SecurityException("closed")
        if ApplicationContext.current() is not self.context.application:
            raise SecurityException("configuration")
        self._active += 1
        self._idle.clear()
        try:
            yield
        finally:
            self._active -= 1
            if not self._active:
                self._idle.set()

    async def _call(self, callback):
        try:
            async with asyncio.timeout(self.settings.provider_timeout_seconds):
                return await callback()
        except SecurityException:
            raise
        except BaseBusinessException as error:
            if 400 <= error.http_status < 500:
                raise
            raise SecurityException("unavailable", cause=error) from error
        except Exception as error:
            raise SecurityException("unavailable", cause=error) from error

    def _domain(self, policy: RoutePolicy) -> str:
        domain = self.settings.default_domain if policy.domain is None else policy.domain
        if domain not in self.settings.domains:
            raise SecurityException("configuration")
        return domain

    async def _lookup(self, token: str, domain: str) -> LoginSession:
        digest = OpaqueToken.digest(token)
        session = await self._call(
            lambda: self.tokens.resolve(
                digest,
                application_id=self.settings.application_id,
                domain=domain,
            )
        )
        if session is None:
            raise SecurityException("invalid")
        if not isinstance(session, LoginSession):
            raise SecurityException("configuration")
        if session.application_id != self.settings.application_id or session.domain != domain:
            raise SecurityException("invalid")
        if not hmac.compare_digest(session.token_digest, digest):
            raise SecurityException("invalid")
        return session

    async def _resolve(self, token: str, domain: str) -> LoginSession:
        session = await self._lookup(token, domain)
        self._validate(session, domain)
        return session

    def _validate(self, session: LoginSession, domain: str) -> None:
        if not isinstance(session, LoginSession):
            raise SecurityException("configuration")
        if session.application_id != self.settings.application_id or session.domain != domain:
            raise SecurityException("invalid")
        if session.expires_at <= datetime.now(timezone.utc):
            raise SecurityException("expired")
        if session.revoked:
            raise SecurityException("revoked")
        if not session.account_enabled:
            raise SecurityException("disabled")
        if session.credential_revision != session.current_credential_revision:
            raise SecurityException("credentials")

    @staticmethod
    def binding(session: LoginSession) -> str:
        values = [
            session.application_id,
            session.domain,
            session.account_id,
            session.session_id,
            session.family_id,
            session.realm.value,
            session.tenant_id,
            session.membership_id,
            session.authority_tenant_id,
            session.authority_membership_id,
            session.platform_operator_id,
            session.support_session_id,
            None if session.access_mode is None else session.access_mode.value,
            session.group_id,
            session.management_relation_id,
            session.approved_resource,
            session.approved_action,
        ]
        return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()

    def _permission_identifier(self, session: LoginSession) -> str:
        revision = hashlib.sha256(session.authorization_revision.encode()).hexdigest()
        return f"{session.application_id}:{session.domain}:{self.binding(session)}:{revision}"

    async def _snapshot(self, session: LoginSession) -> PermissionSnapshot:
        binding = self.binding(session)

        async def load():
            snapshot = await self.permissions.snapshot(session, binding=binding)
            self._validate_snapshot(snapshot, session, binding)
            return snapshot.model_dump(mode="json")

        if self.settings.permission_cache_enabled:
            value = await self._call(
                lambda: self.cache.get_or_load(
                    self.settings.cache_key(),
                    self._permission_identifier(session),
                    load,
                    self.settings.permission_cache_ttl_seconds,
                    wait_seconds=self.settings.provider_timeout_seconds,
                    critical_section_timeout_seconds=self.settings.provider_timeout_seconds,
                    lease_seconds=self.settings.provider_timeout_seconds + 1,
                )
            )
        else:
            value = await self._call(load)
        try:
            snapshot = PermissionSnapshot.model_validate_json(json.dumps(value))
        except (TypeError, ValueError) as error:
            raise SecurityException("unavailable", cause=error) from error
        self._validate_snapshot(snapshot, session, binding)
        return snapshot

    @staticmethod
    def _validate_snapshot(snapshot, session, binding):
        if (
            not isinstance(snapshot, PermissionSnapshot)
            or snapshot.binding != binding
            or snapshot.revision != session.authorization_revision
        ):
            raise SecurityException("unavailable")

    async def invalidate_permissions(self, session: LoginSession) -> None:
        """删除明确版本的缓存；版本推进由业务与权限变更原子提交。"""
        async with self._operation():
            if (
                session.application_id != self.settings.application_id
                or session.domain not in self.settings.domains
            ):
                raise SecurityException("invalid")
            if self.settings.permission_cache_enabled:
                await self._call(
                    lambda: self.cache.delete(
                        self.settings.cache_key(), self._permission_identifier(session)
                    )
                )

    def validate_policy(self, policy: RoutePolicy) -> None:
        """路由发布前校验部署与认证域；独立任务也复用同一契约。"""
        if policy.requires_identity:
            self._domain(policy)
        if (
            policy.realm in {SecurityRealm.TENANT, SecurityRealm.SUPPORT}
            or policy.tenant_required
            or policy.required_capability is not None
        ) and self._tenant is None:
            raise SecurityException("configuration")
        if policy.required_capability is not None and not self._tenant.supports(
            policy.required_capability
        ):
            raise SecurityException("configuration")

    async def _check_policy(self, session: LoginSession, policy: RoutePolicy):
        self.validate_policy(policy)
        if not policy.requires_identity:
            raise SecurityException("configuration")
        if policy.realm is not None and session.realm is not policy.realm:
            raise SecurityException("denied")
        if policy.tenant_required and session.tenant_id is None:
            raise SecurityException("denied")
        if session.realm is SecurityRealm.TENANT:
            allowed = (
                policy.allowed_tenant_access_modes
                if policy.allowed_tenant_access_modes is not None
                else frozenset({TenantAccessMode.DIRECT_MEMBERSHIP})
            )
            if session.access_mode not in allowed:
                raise SecurityException("denied")
        if session.realm is SecurityRealm.SUPPORT and (
            policy.realm is not SecurityRealm.SUPPORT
            or session.approved_resource != policy.required_support_resource
            or session.approved_action != policy.required_support_action
        ):
            raise SecurityException("denied")
        if (
            policy.required_entitlement is not None
            and policy.required_entitlement not in session.effective_capabilities
        ):
            raise SecurityException("denied")
        if not self._matches(session.scopes, policy.scopes, policy.scope_mode):
            raise SecurityException("denied")
        if policy.permissions or policy.roles:
            snapshot = await self._snapshot(session)
            check = (
                PermissionPolicy.all if policy.permission_mode == "all" else PermissionPolicy.any
            )
            if policy.permissions and not check(snapshot.permissions, policy.permissions):
                raise SecurityException("denied")
            if not self._matches(snapshot.roles, policy.roles, policy.role_mode):
                raise SecurityException("denied")

    @staticmethod
    def _matches(granted, required, mode):
        if not required:
            return True
        return (
            set(required).issubset(granted)
            if mode == "all"
            else not set(required).isdisjoint(granted)
        )

    @asynccontextmanager
    async def _authorized_session(self, session: LoginSession, policy: RoutePolicy):
        await self._check_policy(session, policy)
        if session.tenant_id is not None:
            if self._tenant is None:
                raise SecurityException("configuration")
            async with self._tenant_scope(self._tenant.enter(session, policy)):
                self.context._install(session)
                yield session
        else:
            self.context._install(session)
            yield session

    @asynccontextmanager
    async def _tenant_scope(self, manager):
        # Tenant 独占准入与隔离；Security 保护完整退出，不允许其吞掉业务异常。
        if manager is None:
            raise SecurityException("configuration")
        await self._call(manager.__aenter__)
        primary = None
        try:
            yield
        except BaseException as error:
            primary = error
        finally:
            # ContextVar token 必须在创建它的 Context 内复位；普通任务复制会破坏它。
            exit_task = asyncio.Task(
                manager.__aexit__(
                    type(primary) if primary is not None else None,
                    primary,
                    primary.__traceback__ if primary is not None else None,
                ),
                context=asyncio.current_task().get_context(),
                name="security-tenant-exit",
                loop=asyncio.get_running_loop(),
                eager_start=False,
            )
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                lambda: exit_task,
                "Security 租户作用域清理",
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "租户作用域退出失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )

    @asynccontextmanager
    async def authorized(
        self, token: str, policy: RoutePolicy, *, request_audit: RequestAudit | None = None
    ):
        async with self._operation():
            with self.context._scope(request_audit):
                session = await self._resolve(token, self._domain(policy))
                async with self._authorized_session(session, policy):
                    yield session

    async def run(self, token: str, policy: RoutePolicy, callback, *args, **kwargs):
        """任务重新验证令牌，不继承调用者的可信身份。"""

        async def invoke():
            async with self.authorized(token, policy):
                return await callback(*args, **kwargs)

        return await self.context.application.tasks.run_isolated(invoke)

    async def logout(self, token: str, *, domain: str | None = None) -> None:
        async with self._operation():
            session = await self._lookup(token, self._domain(RoutePolicy(domain=domain)))
            # 撤销可能已经提交；取消必须等提供者操作终态，不报告伪成功。
            try:
                await AsyncioUtils.run_cancellation_shielded(
                    self._call(lambda: self.tokens.revoke(session))
                )
            finally:
                self.context.invalidate(session.family_id)

    async def _live_current(self) -> LoginSession:
        current = self.context.require()
        latest = await self._call(
            lambda: self.tokens.resolve(
                current.token_digest,
                application_id=self.settings.application_id,
                domain=current.domain,
            )
        )
        if latest is None:
            raise SecurityException("invalid")
        self._validate(latest, current.domain)
        if latest.token_digest != current.token_digest or self.binding(latest) != self.binding(
            current
        ):
            raise SecurityException("invalid")
        return latest

    async def has_permissions(self, *permissions: str, any_of: bool = False) -> bool:
        """显式业务权限判断重验当前会话，适用于长任务中的再次授权。"""
        async with self._operation():
            current = await self._live_current()
            snapshot = await self._snapshot(current)
            check = PermissionPolicy.any if any_of else PermissionPolicy.all
            return bool(permissions) and check(snapshot.permissions, permissions)

    async def has_roles(self, *roles: str, any_of: bool = False) -> bool:
        async with self._operation():
            current = await self._live_current()
            snapshot = await self._snapshot(current)
            return bool(roles) and (
                not set(roles).isdisjoint(snapshot.roles)
                if any_of
                else set(roles).issubset(snapshot.roles)
            )

    async def has_scopes(self, *scopes: str, any_of: bool = False) -> bool:
        async with self._operation():
            current = await self._live_current()
            return bool(scopes) and (
                not set(scopes).isdisjoint(current.scopes)
                if any_of
                else set(scopes).issubset(current.scopes)
            )

    async def require_enum_permission(self, code, enum_class) -> None:
        async with self._operation():
            session = await self._live_current()
            member = enum_class.get_by_code(code)
            if member is None:
                raise SecurityException("denied")
            permission = member.permission
            if permission is not None:
                snapshot = await self._snapshot(session)
                if not PermissionPolicy.all(snapshot.permissions, (permission,)):
                    raise SecurityException("denied")

    async def issue_message(self, payload: bytes, *, audience: str) -> bytes:
        async with self._operation():
            session = self.context.require()
            if session.realm is not SecurityRealm.TENANT:
                raise SecurityException("denied")
            if self._messages is None or not audience:
                raise SecurityException("configuration")
            if not isinstance(payload, bytes):
                raise SecurityException("invalid")
            return await self._call(
                lambda: self._messages.issue(session, payload, audience=audience)
            )

    async def run_message(
        self,
        proof: bytes,
        payload: bytes,
        policy: RoutePolicy,
        callback,
        *args,
        audience: str,
        **kwargs,
    ):
        async def invoke():
            async with self._operation():
                with self.context._scope():
                    if self._messages is None or not audience:
                        raise SecurityException("configuration")
                    if (
                        not isinstance(proof, bytes)
                        or not 1 <= len(proof) <= 65536
                        or not isinstance(payload, bytes)
                    ):
                        raise SecurityException("invalid")
                    domain = self._domain(policy)
                    session = await self._call(
                        lambda: self._messages.verify(
                            proof,
                            payload,
                            application_id=self.settings.application_id,
                            domain=domain,
                            audience=audience,
                        )
                    )
                    self._validate(session, domain)
                    if session.realm is not SecurityRealm.TENANT:
                        raise SecurityException("denied")
                    async with self._authorized_session(session, policy):
                        return await callback(payload, *args, **kwargs)

        return await self.context.application.tasks.run_isolated(invoke)

    async def issue_workload_message(
        self, payload: bytes, *, audience: str, capability: str
    ) -> bytes:
        """系统来源只能传播已认证能力，不能把普通用户或平台会话升级为系统来源。"""
        async with self._operation():
            identity = self.context.current_workload()
            if identity is None or capability not in identity.capabilities:
                raise SecurityException("denied")
            if self._messages is None or not audience:
                raise SecurityException("configuration")
            if not isinstance(payload, bytes):
                raise SecurityException("invalid")
            return await self._call(
                lambda: self._messages.issue_workload(
                    identity,
                    payload,
                    audience=audience,
                    capability=capability,
                )
            )

    async def run_workload_message(
        self,
        proof: bytes,
        payload: bytes,
        callback,
        *args,
        audience: str,
        capability: str,
        domain: str | None = None,
        **kwargs,
    ):
        """服务身份由消息提供者认证；系统能力必须由消费端显式声明。"""

        async def invoke():
            async with self._operation():
                with self.context._scope():
                    if self._messages is None or not audience or not capability:
                        raise SecurityException("configuration")
                    if (
                        not isinstance(proof, bytes)
                        or not 1 <= len(proof) <= 65536
                        or not isinstance(payload, bytes)
                    ):
                        raise SecurityException("invalid")
                    selected_domain = self._domain(RoutePolicy(domain=domain))
                    message = await self._call(
                        lambda: self._messages.verify_workload(
                            proof,
                            payload,
                            application_id=self.settings.application_id,
                            domain=selected_domain,
                            audience=audience,
                        )
                    )
                    if not isinstance(message, WorkloadMessage):
                        raise SecurityException("configuration")
                    if message.capability != capability:
                        raise SecurityException("denied")
                    self._validate_workload(message.identity, selected_domain, audience, capability)
                    identity = message.identity.model_copy(
                        update={"capabilities": frozenset({capability})}
                    )
                    async with self._workload_scope(identity, capability):
                        return await callback(payload, *args, **kwargs)

        return await self.context.application.tasks.run_isolated(invoke)

    def _validate_workload(self, identity, domain, audience, capability):
        if not isinstance(identity, WorkloadIdentity):
            raise SecurityException("configuration")
        if (identity.application_id, identity.domain, identity.audience) != (
            self.settings.application_id,
            domain,
            audience,
        ):
            raise SecurityException("invalid")
        if identity.expires_at <= datetime.now(timezone.utc):
            raise SecurityException("expired")
        if capability not in identity.capabilities:
            raise SecurityException("denied")

    @asynccontextmanager
    async def _workload_scope(self, identity, capability):
        if identity.tenant_id is None:
            self.context._install_workload(identity)
            yield
        else:
            if self._tenant is None:
                raise SecurityException("configuration")
            async with self._tenant_scope(self._tenant.enter_workload(identity, capability)):
                self.context._install_workload(identity)
                yield

    async def run_workload(
        self,
        source: str,
        callback,
        *args,
        capability: str,
        tenant_id: str | None = None,
        domain: str | None = None,
        **kwargs,
    ):
        """本地 Job 经过服务提供者认证；无租户模式不继承父请求租户。"""

        async def invoke():
            async with self._operation():
                with self.context._scope():
                    if self._workloads is None or not source or not capability:
                        raise SecurityException("configuration")
                    selected_domain = self._domain(RoutePolicy(domain=domain))
                    identity = await self._call(
                        lambda: self._workloads.authenticate(
                            source,
                            application_id=self.settings.application_id,
                            domain=selected_domain,
                            capability=capability,
                            tenant_id=tenant_id,
                        )
                    )
                    self._validate_workload(identity, selected_domain, source, capability)
                    if identity.tenant_id != tenant_id:
                        raise SecurityException("invalid")
                    async with self._workload_scope(identity, capability):
                        return await callback(*args, **kwargs)

        return await self.context.application.tasks.run_isolated(invoke)

    async def close(self) -> None:
        if self._close_task is None:
            self._phase = "closing"
            self._close_task = asyncio.create_task(
                self._close(), name="security-close", context=Context()
            )
        await asyncio.shield(self._close_task)

    async def _close(self):
        await self._idle.wait()
        self._tenant = self._messages = self._workloads = None
        self._phase = "closed"

    def resources(self) -> dict:
        return {"state": self._phase, "active_operations": self._active}
