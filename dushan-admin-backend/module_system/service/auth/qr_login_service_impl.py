import hashlib
import hmac
import secrets
import time

from user_agents import parse as parse_user_agent

from framework.common.exception import ServiceException
from framework.starter_cache.public import CacheHandler
from framework.starter_di.public import Inject, service
from framework.starter_security.public import (
    LoginSession,
    SecurityContext,
    SecurityException,
    SecurityRealm,
    SecurityService,
)
from framework.starter_tenant.public import TenantContext
from framework.starter_web.public import RequestContext, RoutePolicy
from module_system.config.qr_login_settings import QrLoginSettings
from module_system.controller.admin.auth.vo.auth.auth_login_resp_vo import AuthLoginRespVO
from module_system.controller.admin.auth.vo.qr_login.auth_qr_create_resp_vo import (
    AuthQrCreateRespVO,
)
from module_system.controller.admin.auth.vo.qr_login.auth_qr_scan_resp_vo import AuthQrScanRespVO
from module_system.controller.admin.auth.vo.qr_login.auth_qr_status_resp_vo import (
    AuthQrStatusRespVO,
)
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.constants.qr_login_script_constants import QrLoginScriptConstants
from module_system.definitions.enums.auth.qr_login_status_enum import QrLoginStatusEnum
from module_system.service.auth.auth_admin_auth_service import AuthAdminAuthService
from module_system.service.auth.bo.qr_login_state_bo import QrLoginStateBO
from module_system.service.auth.qr_login_service import QrLoginService


@service(interface=QrLoginService)
class QrLoginServiceImpl(QrLoginService):
    settings: QrLoginSettings = Inject()
    cache: CacheHandler = Inject()
    tenant: TenantContext = Inject()
    identity: SecurityContext = Inject()
    security: SecurityService = Inject()
    auth: AuthAdminAuthService = Inject()

    def require_enabled(self):
        if not self.settings.enabled:
            raise ServiceException(ErrorCodeConstants.AUTH_QR_DISABLED)

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    async def create(self, binding: str, origin: str) -> AuthQrCreateRespVO:
        self.require_enabled()
        token = secrets.token_urlsafe(32)
        request = RequestContext.current()
        agent = parse_user_agent(request.user_agent[:512])
        state = QrLoginStateBO(
            status=QrLoginStatusEnum.WAITING,
            tenant_id=self.tenant.get_required_tenant_id(),
            binding_digest=self.digest(binding),
            origin=origin,
            code=f"{secrets.randbelow(1000000):06d}",
            browser=f"{agent.browser.family} {agent.browser.version_string} · {agent.os.family}".strip(),
            ip=request.client_ip_text,
            expires_at=int(time.time() * 1000) + self.settings.expire_seconds * 1000,
            approver=None,
        )
        result = await self.cache.eval_atomic(
            SystemCacheKeyConstants.QR_LOGIN,
            (self.digest(token),),
            QrLoginScriptConstants.CREATE,
            (state.model_dump_json(), self.settings.expire_seconds),
        )
        if result != "OK":
            raise ServiceException(ErrorCodeConstants.AUTH_QR_CHANGED)
        return AuthQrCreateRespVO(
            ticket=token,
            code=state.code,
            tenant_id=state.tenant_id,
            expires_at=state.expires_at,
            poll_interval=2000,
        )

    async def _read(self, token: str):
        self.require_enabled()
        raw = await self.cache.eval_atomic(
            SystemCacheKeyConstants.QR_LOGIN,
            (self.digest(token),),
            QrLoginScriptConstants.READ,
        )
        if raw is None:
            return None
        return raw, QrLoginStateBO.model_validate_json(raw)

    async def _require(self, token: str):
        value = await self._read(token)
        if value is None:
            raise ServiceException(ErrorCodeConstants.AUTH_QR_EXPIRED)
        return value

    def _browser(self, state: QrLoginStateBO, binding: str, origin: str):
        if (
            not hmac.compare_digest(state.binding_digest, self.digest(binding))
            or state.origin != origin
        ):
            raise ServiceException(ErrorCodeConstants.AUTH_QR_BROWSER)

    def _phone(self, state: QrLoginStateBO) -> LoginSession:
        identity = self.identity.require()
        if identity.realm is not SecurityRealm.TENANT or identity.tenant_id != state.tenant_id:
            raise ServiceException(ErrorCodeConstants.AUTH_QR_TENANT)
        if state.approver is not None and (
            identity.account_id != state.approver.account_id
            or identity.family_id != state.approver.family_id
        ):
            raise ServiceException(ErrorCodeConstants.AUTH_QR_CHANGED)
        return identity

    async def _transition(self, token: str, raw: str, state: QrLoginStateBO | None):
        result = await self.cache.eval_atomic(
            SystemCacheKeyConstants.QR_LOGIN,
            (self.digest(token),),
            QrLoginScriptConstants.TRANSITION,
            (raw, "consume" if state is None else state.model_dump_json()),
        )
        if result == "expired":
            raise ServiceException(ErrorCodeConstants.AUTH_QR_EXPIRED)
        if result != "ok":
            raise ServiceException(ErrorCodeConstants.AUTH_QR_CHANGED)

    async def poll(self, token: str, binding: str, origin: str) -> AuthQrStatusRespVO:
        found = await self._read(token)
        if found is None:
            return AuthQrStatusRespVO(status=QrLoginStatusEnum.EXPIRED)
        _, state = found
        self._browser(state, binding, origin)
        return AuthQrStatusRespVO(status=state.status)

    async def scan(self, token: str) -> AuthQrScanRespVO:
        raw, state = await self._require(token)
        identity = self._phone(state)
        if state.status is QrLoginStatusEnum.WAITING:
            state.status = QrLoginStatusEnum.SCANNED
            state.approver = identity
            await self._transition(token, raw, state)
        elif state.status is not QrLoginStatusEnum.SCANNED:
            raise ServiceException(ErrorCodeConstants.AUTH_QR_CHANGED)
        return AuthQrScanRespVO(
            status=state.status,
            tenant_id=state.tenant_id,
            code=state.code,
            browser=state.browser,
            ip=state.ip,
            expires_at=state.expires_at,
        )

    async def confirm(self, token: str, approve: bool) -> None:
        raw, state = await self._require(token)
        identity = self._phone(state)
        if state.status is not QrLoginStatusEnum.SCANNED:
            raise ServiceException(ErrorCodeConstants.AUTH_QR_CHANGED)
        state.status = QrLoginStatusEnum.APPROVED if approve else QrLoginStatusEnum.CANCELLED
        state.approver = identity
        await self._transition(token, raw, state)

    async def cancel(self, token: str, binding: str, origin: str) -> None:
        found = await self._read(token)
        if found is None:
            return
        raw, state = found
        self._browser(state, binding, origin)
        if state.status is QrLoginStatusEnum.CANCELLED:
            return
        state.status = QrLoginStatusEnum.CANCELLED
        await self._transition(token, raw, state)

    async def consume(self, token: str, binding: str, origin: str) -> AuthLoginRespVO:
        raw, state = await self._require(token)
        self._browser(state, binding, origin)
        if state.status is not QrLoginStatusEnum.APPROVED or state.approver is None:
            raise ServiceException(ErrorCodeConstants.AUTH_QR_CHANGED)
        # 先原子消费，签发中断时要求重新扫码，不能并发签发多个电脑会话。
        await self._transition(token, raw, None)
        request = RequestContext.current()

        async def issue(identity: LoginSession):
            # 身份复验在隔离执行内运行，显式保留此次电脑请求的审计信息。
            with RequestContext.bind(request.connection, request.request_id, request.client_ip):
                return await self.auth.qr_login(identity)

        try:
            return await self.security.run_session_reference(
                state.approver,
                RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
                issue,
            )
        except SecurityException as error:
            raise ServiceException(ErrorCodeConstants.AUTH_QR_IDENTITY_CHANGED) from error
