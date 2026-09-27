from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.starter_web.response.middleware_result import MiddlewareResult
from framework.starter_web.routing.route_policy import RoutePolicy


class TenantSelectorMiddleware:
    """拒绝旧选择头；规范头交给路由匹配后的入口策略，不提前绑定上下文。"""

    HEADERS = frozenset({b"tenant-id", b"visit-tenant-id"})

    def __init__(self, app):
        self.app = app
        self.result = MiddlewareResult()

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        names = {name.lower() for name, _ in scope["headers"]}
        blocked = bool(names & self.HEADERS) or (
            RoutePolicy.TENANT_HEADER.lower().encode() in names
            and (scope["type"] == "websocket" or scope["app"].state.security is None)
        )
        if blocked:
            if scope["type"] == "websocket":
                await send(
                    {"type": "websocket.close", "code": 4002, "reason": "tenant selector rejected"}
                )
            else:
                response = self.result.error_response(
                    GlobalErrorCodeConstants.FORBIDDEN, "该入口不接受此租户请求头"
                )
                await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
