from contextlib import AbstractAsyncContextManager
from typing import Protocol, runtime_checkable

from fastapi import Request

from framework.common.security.request_identity import RequestIdentity
from framework.starter_web.routing.route_policy import RoutePolicy


@runtime_checkable
class RouteGuard(Protocol):
    """在 FastAPI 解析正文前完成访问检查，作用域覆盖完整响应。"""

    def guard(
        self, request: Request, policy: RoutePolicy
    ) -> AbstractAsyncContextManager[RequestIdentity]: ...
