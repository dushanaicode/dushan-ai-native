from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.starter_web.response.middleware_result import MiddlewareResult


class TenantSelectorMiddleware:
    """客户端旧租户头不能改变服务端绑定；无需读取或记录其值。"""

    HEADERS = frozenset({b"tenant-id", b"visit-tenant-id", b"x-tenant-id"})

    def __init__(self, app):
        self.app = app
        self.result = MiddlewareResult()

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"} and any(
            name.lower() in self.HEADERS for name, _ in scope["headers"]
        ):
            if scope["type"] == "websocket":
                await send(
                    {"type": "websocket.close", "code": 4002, "reason": "tenant selector rejected"}
                )
            else:
                response = self.result.error_response(
                    GlobalErrorCodeConstants.FORBIDDEN, "租户由服务端会话绑定，不接受租户请求头"
                )
                await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
