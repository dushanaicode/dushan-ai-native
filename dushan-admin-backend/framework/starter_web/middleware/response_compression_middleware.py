from starlette.datastructures import Headers
from starlette.middleware.gzip import GZipMiddleware

from framework.starter_web.middleware.length_preserving_gzip_responder import (
    LengthPreservingGZipResponder,
)


class ResponseCompressionMiddleware(GZipMiddleware):
    """原生 GZip 行为，补入按请求保留定长流的宿主策略。"""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and "gzip" in Headers(scope=scope).get("Accept-Encoding", ""):
            responder = LengthPreservingGZipResponder(
                self.app, self.minimum_size, self.compresslevel, scope
            )
            await responder(scope, receive, send)
        else:
            await super().__call__(scope, receive, send)
