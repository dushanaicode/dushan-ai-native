from starlette.types import Receive, Scope, Send

from framework.starter_web.response.file_content_response import FileContentResponse
from framework.starter_web.response.streaming_result import StreamingResult


class FileStreamingResponse(StreamingResult):
    """为文件内存流增加条件读取，沿用 StreamingResult 的流关闭契约。"""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """条件匹配时不开始迭代内存内容，否则正常发送并释放流。"""
        response = FileContentResponse.not_modified_response(self, scope)
        if response is not None:
            await self._source.aclose()
            await response(scope, receive, send)
        else:
            await super().__call__(scope, receive, send)
