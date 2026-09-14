from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class ReadinessMiddleware:
    """启动审计完成前不分派业务请求；未就绪探针继续使用标准 HTTP 503。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            state = scope["app"].state
            if not state.bootstrap.ready or not state.web_routes.published:
                response = JSONResponse(
                    status_code=503,
                    content={
                        "code": 503,
                        "message": "服务尚未就绪",
                        "error": None,
                        "data": {
                            "status": "not_ready",
                            "version": state.bootstrap.settings.version,
                        },
                    },
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
