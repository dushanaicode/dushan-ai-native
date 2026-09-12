from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["服务状态"])


@router.get("/health", summary="检查服务启动状态", response_class=JSONResponse)
async def health(request: Request) -> JSONResponse:
    """检查服务是否已完成启动，尚未就绪时返回 503。"""
    ctx = request.app.state.bootstrap
    database = request.app.state.database
    ready = ctx.ready and (database is None or database.is_ready)
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "code": 0 if ready else 503,
            "message": "服务就绪" if ready else "服务尚未就绪",
            "error": None,
            "data": {
                "status": "ready" if ready else "not_ready",
                "version": ctx.settings.version,
            },
        },
    )
