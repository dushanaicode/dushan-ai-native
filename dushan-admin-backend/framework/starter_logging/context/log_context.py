import contextvars
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class LogContext:
    """在当前异步上下文传播请求、追踪、身份和来源信息。

    请求开始用 begin_request 获取 token，结束时用 reset(token) 恢复上层上下文。
    current 返回不可变快照，set_principal 等方法通过替换快照更新字段。
    子任务继承创建时的快照，各任务后续更新相互独立。
    """

    request_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    tenant_id: str | int | None = None
    account_id: str | int | None = None
    membership_id: str | int | None = None
    realm: str | None = None
    client_ip: str | None = None

    @classmethod
    def current(cls) -> "LogContext":
        """读取当前上下文中的日志字段快照。"""
        return _log_context_var.get()

    @classmethod
    def begin_request(cls, request_id: str) -> contextvars.Token:
        """为新 HTTP 请求发布全新快照，阻断父协程旧上下文。"""
        return _log_context_var.set(cls(request_id=request_id))

    @classmethod
    def bind_trace(cls, trace_id: str | None, span_id: str | None) -> contextvars.Token:
        """绑定追踪标识并返回可恢复旧快照的 token。"""
        return _log_context_var.set(replace(cls.current(), trace_id=trace_id, span_id=span_id))

    @classmethod
    def set_tenant(cls, tenant_id: str | int | None) -> None:
        """更新当前日志快照的租户标识。"""
        _log_context_var.set(replace(cls.current(), tenant_id=tenant_id))

    @classmethod
    def set_principal(
        cls,
        account_id: str | int | None,
        membership_id: str | int | None,
        realm: str | None,
    ) -> None:
        """发布当前 Principal 的明确身份字段。"""
        _log_context_var.set(
            replace(
                cls.current(),
                account_id=account_id,
                membership_id=membership_id,
                realm=realm,
            )
        )

    @classmethod
    def bind_principal(cls, account_id, tenant_id, membership_id, realm) -> contextvars.Token:
        """保存可恢复的安全投影，保留当前请求和追踪信息。"""
        return _log_context_var.set(
            replace(
                cls.current(),
                account_id=account_id,
                tenant_id=tenant_id,
                membership_id=membership_id,
                realm=realm,
            )
        )

    @classmethod
    def set_client_ip(cls, client_ip: str | None) -> None:
        """更新当前日志快照的客户端 IP。"""
        _log_context_var.set(replace(cls.current(), client_ip=client_ip))

    @staticmethod
    def reset(token: contextvars.Token) -> None:
        """恢复 token 对应的上层日志上下文。"""
        _log_context_var.reset(token)

    @classmethod
    def clear(cls) -> None:
        """将当前日志上下文重置为空快照。"""
        _log_context_var.set(cls())


_log_context_var: contextvars.ContextVar[LogContext] = contextvars.ContextVar(
    "logging_context",
    default=LogContext(),
)
