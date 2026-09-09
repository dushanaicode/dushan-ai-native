"""不依赖数据库或登录状态的启动就绪检查。"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["服务状态"])


@router.get("/health", summary="检查服务启动状态", response_class=JSONResponse)
async def health(request: Request) -> JSONResponse:
    """只在全部基础启动步骤完成后返回成功。"""
    ctx = request.app.state.bootstrap
    ready = ctx.ready
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "code": 0 if ready else 503,
            "message": "服务就绪" if ready else "服务尚未就绪",
            "data": {
                "status": "ready" if ready else "not_ready",
                "version": ctx.settings.version,
            },
        },
    )
