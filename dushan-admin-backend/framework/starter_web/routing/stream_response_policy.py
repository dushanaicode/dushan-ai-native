import inspect
from dataclasses import dataclass

from fastapi.sse import EventSourceResponse
from starlette.requests import Request
from starlette.responses import FileResponse, Response, StreamingResponse

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_web.response.stream_integrity import StreamIntegrity


@dataclass(frozen=True, slots=True)
class StreamResponsePolicy:
    """宿主显式提供引擎；在响应对象装配完成、调用 ASGI 发送之前检查原始流。"""

    engine: str

    async def prepare(
        self, response: Response, request: Request, endpoint, *, native_sse: bool
    ) -> Response:
        if (
            self.engine != "granian"
            or request.method == "HEAD"
            or response.status_code in {204, 304}
        ):
            return response
        if isinstance(response, FileResponse):
            request.scope["state"]["web_preserve_stream_length"] = True
            return response
        if (
            not isinstance(response, StreamingResponse)
            or native_sse
            or isinstance(response, EventSourceResponse)
        ):
            return response
        declared = getattr(endpoint, StreamIntegrity.ATTRIBUTE, None)
        integrity = getattr(response, StreamIntegrity.ATTRIBUTE, declared)
        if declared is not None and integrity != declared:
            raise ValueError("路由与响应的流完整性声明冲突")
        length = response.headers.get("content-length")
        if length is not None and (not length.isascii() or not length.isdecimal()):
            raise ValueError("流 Content-Length 必须是非负十进制字节数")
        if length is None and integrity is None:
            # 尚未启动迭代；关闭已明确支持 aclose 的异步生成器，不读取任何数据。
            if inspect.isasyncgen(response.body_iterator):
                error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                    response.body_iterator.aclose, "拒绝原始响应流"
                )
                CleanupUtils.raise_collected_cleanup_errors(
                    "关闭被拒绝的响应流失败",
                    [] if error is None else [error],
                    caller_cancellation=cancellation,
                )
            raise ValueError(
                "Granian 原始流必须提供 Content-Length 或 StreamIntegrity 声明；无完整性协议的原始流请使用 Uvicorn"
            )
        if length is not None:
            # 流式 GZip 会移除 Content-Length；保留已选择的长度完整性边界。
            request.scope["state"]["web_preserve_stream_length"] = True
        return response
