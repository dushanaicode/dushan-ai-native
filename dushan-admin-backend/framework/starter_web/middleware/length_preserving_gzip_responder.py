from starlette.middleware.gzip import GZipResponder


class LengthPreservingGZipResponder(GZipResponder):
    """继续使用 Starlette 压缩器，仅对宿主选定的定长流保留原字节和长度。"""

    def __init__(self, app, minimum_size, compresslevel, scope):
        super().__init__(app, minimum_size, compresslevel)
        self.scope = scope

    def apply_compression(self, body: bytes, *, more_body: bool) -> bytes:
        if self.scope.get("state", {}).get("web_preserve_stream_length", False):
            return body
        return super().apply_compression(body, more_body=more_body)
