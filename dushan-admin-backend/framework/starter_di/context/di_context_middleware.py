from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from framework.common.exception.utils.response_builder import ExceptionResponseBuilder
from framework.starter_di.exception.di_exception import DiException


class DiContextMiddleware:
    """纯 ASGI 执行边界覆盖完整响应、流和 WebSocket，不在返回 Response 时提前退出。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        application = scope["app"].state.application_context
        if application is None or not application.settings.automatic_context_binding:
            await self.app(scope, receive, send)
            return
        try:
            binding = application.reserve_execution()
        except DiException as error:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1013})
            else:
                response = JSONResponse(
                    status_code=503,
                    content=ExceptionResponseBuilder.build(
                        error.error_code, error.error_code.description, exc=error, debug=False
                    ),
                )
                await response(scope, receive, send)
            return
        try:
            with application.activate(binding):
                await self.app(scope, receive, send)
        finally:
            application.release_execution(binding)
