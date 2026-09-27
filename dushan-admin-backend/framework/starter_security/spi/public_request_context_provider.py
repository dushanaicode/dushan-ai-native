from contextlib import AbstractAsyncContextManager
from typing import Protocol, runtime_checkable

from fastapi import Request


@runtime_checkable
class PublicRequestContextProvider(Protocol):
    """应用登记的公开入口上下文，名称来自已发布的路由元数据。"""

    def validate(self, name: str) -> None: ...

    def parameters(self, name: str) -> tuple[dict, ...]: ...

    def enter(self, request: Request, name: str) -> AbstractAsyncContextManager[None]: ...
