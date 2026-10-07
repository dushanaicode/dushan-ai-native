from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import ClassVar

from starlette.requests import HTTPConnection

from framework.common.security.request_identity import RequestIdentity


@dataclass(slots=True)
class RequestContext:
    """仅在完整 HTTP 执行内有效；复制到脱离请求的任务也不能延长其寿命。

    connection 提供路径、头和应用归属，不提供正文读取入口。
    正文和上传始终由 FastAPI 注入的 Request、Body、Form、File 处理。
    """

    _current: ClassVar[ContextVar["RequestContext | None"]] = ContextVar(
        "dushan_web_request", default=None
    )
    connection: HTTPConnection
    request_id: str
    client_ip: str | None
    identity: RequestIdentity | None = None
    _active: bool = True

    @property
    def accept_language(self) -> str | None:
        """读取请求语言偏好，具体语言协商交给翻译器。"""
        return self.connection.headers.get("accept-language")

    @property
    def user_agent(self) -> str:
        """读取可选的浏览器标识，缺失时返回空串，长度由使用方的投影约束。"""
        return self.connection.headers.get("user-agent", "")

    @property
    def client_ip_text(self) -> str:
        """提供客户端地址展示文本，缺失时为空串，不用于必填审计字段。"""
        return "" if self.client_ip is None else self.client_ip

    def require_client_ip(self) -> str:
        """取得审计所需的客户端地址，缺失时明确拒绝继续。"""
        if self.client_ip is None:
            raise RuntimeError("当前 HTTP 请求缺少客户端 IP")
        return self.client_ip

    @classmethod
    def current(cls) -> "RequestContext":
        context = cls._current.get()
        if context is None or not context._active:
            raise RuntimeError("当前没有有效的 HTTP 请求上下文")
        return context

    @classmethod
    @contextmanager
    def bind(cls, connection: HTTPConnection, request_id: str, client_ip: str | None):
        context = cls(connection, request_id, client_ip)
        token = cls._current.set(context)
        try:
            yield context
        finally:
            context._active = False
            context.identity = None
            cls._current.reset(token)
