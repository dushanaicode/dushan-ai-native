from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from framework.starter_web.config.web_settings import WebSettings
from framework.starter_web.middleware.request_body_limit import RequestBodyLimit


class BodyLimitMiddleware:
    """按实际消费的字节限制正文；保留 ASGI 分块、背压与 disconnect，不预读或缓存。"""

    def __init__(self, app: ASGIApp, settings: WebSettings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        media_type = headers.get("content-type", "").partition(";")[0].strip().lower()
        limit = (
            self.settings.max_multipart_bytes
            if media_type == "multipart/form-data"
            else self.settings.max_body_bytes
        )
        content_length = headers.get("content-length")
        if content_length is not None and content_length.isascii() and content_length.isdecimal():
            # 比较位数后再转换，避免不可信超长整数字符串进入 int。
            length = content_length.lstrip("0") or "0"
            if len(length) > len(str(limit)) or int(length) > limit:
                raise RequestBodyLimit()
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise RequestBodyLimit()
            return message

        await self.app(scope, limited_receive, send)
