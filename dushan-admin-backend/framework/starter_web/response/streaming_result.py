from collections.abc import AsyncGenerator, Mapping

from anyio import CancelScope
from fastapi.responses import StreamingResponse
from starlette.types import Send

from framework.starter_web.response.media_type_constants import MediaTypeConstants
from framework.starter_web.response.stream_integrity import StreamIntegrity


class StreamingResult(StreamingResponse):
    """发送异步生成器内容，并在结束、断连或取消时关闭生成器。

    例如 return StreamingResult(chunks(), media_type="application/octet-stream")。
    资源应在生成器内部获取和释放；本类不把任意字节流包装成JSON或SSE事件。
    取消若发生在生成器内部的 await，生成器也须用 CancelScope(shield=True) 保护异步释放。
    结构化SSE使用FastAPI原生EventSourceResponse路由及ServerSentEvent。
    """

    def __init__(
        self,
        content: AsyncGenerator[bytes | str, None],
        *,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str = MediaTypeConstants.OCTET_STREAM,
        integrity: StreamIntegrity | None = None,
    ) -> None:
        """明确接管异步生成器关闭责任，不猜测任意迭代对象的清理方法。"""
        if not isinstance(content, AsyncGenerator):
            raise TypeError("StreamingResult 需要可关闭的异步生成器")
        self._source = content
        super().__init__(
            content=content, status_code=status_code, headers=headers, media_type=media_type
        )
        if integrity is not None:
            integrity(self)

    async def stream_response(self, send: Send) -> None:
        """保留原发送异常或取消信号，清理失败作为附注而不是覆盖原故障。"""
        original: BaseException | None = None
        try:
            await super().stream_response(send)
        except BaseException as error:
            original = error
            raise
        finally:
            with CancelScope(shield=True):
                try:
                    await self._source.aclose()
                except BaseException as cleanup_error:
                    if original is None:
                        raise
                    original.add_note(f"响应流清理失败：{type(cleanup_error).__name__}")
