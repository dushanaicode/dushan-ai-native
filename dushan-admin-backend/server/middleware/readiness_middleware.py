from starlette._utils import get_route_path
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class ReadinessMiddleware:
    """启动审计完成前拒绝业务请求：普通 JSON 使用 HTTP 200，健康探针使用 503。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            state = scope["app"].state
            if not state.bootstrap.ready or not state.web_routes.published:
                response = JSONResponse(
                    status_code=503 if get_route_path(scope) == "/health" else 200,
                    headers={"Cache-Control": "no-store"},
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
