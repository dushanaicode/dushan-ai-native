from fastapi.responses import Response
from starlette.datastructures import Headers
from starlette.types import Receive, Scope, Send


class FileContentResponse(Response):
    """发送预生成文件内容，在发送时处理缓存条件请求。"""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """条件匹配时发送无正文的 304，否则发送原始内存内容。"""
        response = self.not_modified_response(self, scope)
        if response is not None:
            await response(scope, receive, send)
        else:
            await super().__call__(scope, receive, send)

    @staticmethod
    def not_modified_response(response: Response, scope: Scope) -> Response | None:
        """从请求读取标签并弱比较，命中时保留文件策略头和后台任务。"""
        if scope["method"] not in {"GET", "HEAD"}:
            return None
        etag = response.headers.get("etag")
        if etag is None:
            return None
        condition = Headers(scope=scope).get("if-none-match", "")
        if not any(
            value.strip() == "*" or value.strip().removeprefix("W/") == etag
            for value in condition.split(",")
        ):
            return None
        headers = {
            name: value
            for name, value in response.headers.items()
            if name not in {"content-length", "content-type"}
        }
        return Response(status_code=304, headers=headers, background=response.background)
