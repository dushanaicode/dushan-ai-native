from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from framework.starter_web.routing.route_policy import RoutePolicy
from server.routing.application_health import ApplicationHealth

health_router = APIRouter(tags=["服务状态"])


class HealthController:
    @staticmethod
    @health_router.get("/health", summary="检查服务运行就绪状态", response_class=JSONResponse)
    @RoutePolicy.public()
    async def health(request: Request) -> JSONResponse:
        """所有已启用的必要组件均可用才返回 200，否则返回 503。"""
        ctx = request.app.state.bootstrap
        components = await ApplicationHealth.check(ctx)
        ready = all(components.values())
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "code": 0 if ready else 503,
                "message": "服务就绪" if ready else "服务尚未就绪",
                "error": None,
                "data": {
                    "status": "ready" if ready else "not_ready",
                    "version": ctx.settings.version,
                    "components": {
                        name: "ready" if healthy else "not_ready"
                        for name, healthy in components.items()
                    },
                },
            },
        )
