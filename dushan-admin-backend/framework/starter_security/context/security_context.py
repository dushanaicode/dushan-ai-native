from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from framework.starter_database.spi.current_account_provider import CurrentAccountProvider
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_logging.context.log_context import LogContext
from framework.starter_security.context.security_frame import SecurityFrame
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity


@framework(scope=ComponentScopeEnum.SINGLETON)
class SecurityContext(CurrentAccountProvider):
    """身份仅在同一应用、同一 DI execution 和有效作用域内可读。

    新任务/消息使用 SecurityService.run/run_message 重新认证。Data Permission
    可以读取 current 的可信事实，但必须自行执行数据范围策略；此处不授予范围。
    """

    def __init__(self, application: ApplicationContext):
        self.application = application
        self._frame: ContextVar[SecurityFrame | None] = ContextVar(
            f"security_{id(self)}", default=None
        )

    @contextmanager
    def _scope(self, request_audit=None):
        binding = ApplicationContext.current_execution()
        if binding.application is not self.application:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        frame = SecurityFrame(binding, request_audit=request_audit)
        token = self._frame.set(frame)
        log_token = LogContext.bind_principal(None, None, None, None)
        try:
            yield
        finally:
            frame.active = False
            frame.session = None
            frame.workload = None
            frame.request_audit = None
            self._frame.reset(token)
            LogContext.reset(log_token)

    def _install(self, session: LoginSession) -> None:
        """只供完成验证的边界调用，不接收 HTTP 或消息字段。"""
        frame = self._frame.get()
        if (
            frame is None
            or not frame.active
            or frame.binding is not ApplicationContext.current_execution()
        ):
            raise SecurityException(SecurityErrorCodes.INVALID)
        frame.session = session
        frame.workload = None
        LogContext.set_principal(session.account_id, session.membership_id, session.realm.value)
        LogContext.set_tenant(session.tenant_id)

    def _install_workload(self, identity: WorkloadIdentity) -> None:
        frame = self._frame.get()
        if (
            frame is None
            or not frame.active
            or frame.binding is not ApplicationContext.current_execution()
        ):
            raise SecurityException(SecurityErrorCodes.INVALID)
        frame.session = None
        frame.workload = identity
        LogContext.set_principal(None, None, "system")
        LogContext.set_tenant(identity.tenant_id)

    def current(self) -> LoginSession | None:
        frame = self._frame.get()
        if frame is None or not frame.active or not frame.binding.active:
            return None
        if ApplicationContext.current_execution() is not frame.binding:
            return None
        if frame.session is not None and frame.session.expires_at <= datetime.now(timezone.utc):
            raise SecurityException(SecurityErrorCodes.EXPIRED)
        return frame.session

    def require(self) -> LoginSession:
        session = self.current()
        if session is None:
            raise SecurityException(SecurityErrorCodes.MISSING)
        return session

    def current_workload(self) -> WorkloadIdentity | None:
        frame = self._frame.get()
        if frame is None or not frame.active or not frame.binding.active:
            return None
        if ApplicationContext.current_execution() is not frame.binding:
            return None
        if frame.workload is not None and frame.workload.expires_at <= datetime.now(timezone.utc):
            raise SecurityException(SecurityErrorCodes.EXPIRED)
        return frame.workload

    def invalidate(self, family_id: str) -> None:
        """本站退出后撤销当前作用域的身份投影；不尝试修改其他执行的快照。"""
        frame = self._frame.get()
        current = (
            frame.session
            if frame is not None
            and frame.active
            and frame.binding.active
            and frame.binding is ApplicationContext.current_execution()
            else None
        )
        if current is not None and current.family_id == family_id:
            frame.session = None
            LogContext.set_principal(None, None, None)
            LogContext.set_tenant(None)

    def get_current_account_id(self) -> str | None:
        session = self.current()
        return None if session is None else session.account_id

    def request_audit(self):
        self.require()
        return self._frame.get().request_audit
