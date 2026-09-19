from fastapi.datastructures import DefaultPlaceholder
from fastapi.routing import APIRoute
from fastapi.sse import EventSourceResponse
from starlette.requests import Request

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_web.upload.web_request import WebRequest


class WebRoute(APIRoute):
    """FastAPI 仍只解析一次参数；请求子类仅补上传解析的取消清理。"""

    def __init__(self, *args, stream_policy=None, access_guard=None, **kwargs):
        self.stream_policy = stream_policy
        self.access_guard = access_guard
        super().__init__(*args, **kwargs)

    def get_route_handler(self):
        handler = super().get_route_handler()
        response_class = (
            self.response_class.value
            if isinstance(self.response_class, DefaultPlaceholder)
            else self.response_class
        )
        native_sse = issubclass(response_class, EventSourceResponse)

        async def handle(request: Request):
            adapted = WebRequest(request.scope, request.receive)
            if self.access_guard is not None:
                await request.scope["fastapi_inner_astack"].enter_async_context(
                    self.access_guard(adapted)
                )
            # 复用 FastAPI 覆盖完整响应和后台任务的原生退出栈，包含手动 request.form()。
            request.scope["fastapi_inner_astack"].push_async_callback(self._close_request, adapted)
            response = await handler(adapted)
            if self.stream_policy is not None:
                response = await self.stream_policy.prepare(
                    response, adapted, self.endpoint, native_sse=native_sse
                )
            return response

        return handle

    @staticmethod
    async def _close_request(request: WebRequest) -> None:
        error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
            request.close, "HTTP 表单关闭"
        )
        CleanupUtils.raise_collected_cleanup_errors(
            "HTTP 表单关闭失败", [] if error is None else [error], caller_cancellation=cancellation
        )
