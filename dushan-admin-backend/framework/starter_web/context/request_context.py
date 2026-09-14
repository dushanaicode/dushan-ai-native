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
