from starlette.types import ASGIApp, Message, Receive, Scope, Send


class HttpProtocolMiddleware:
    """在最外层保持 HEAD、204/304 的无正文语义，不改写业务状态或响应头。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        bodyless = scope["method"] == "HEAD"

        async def protocol_send(message: Message) -> None:
            nonlocal bodyless
            if message["type"] == "http.response.start":
                bodyless = bodyless or message["status"] in {204, 304}
                if message["status"] == 204:
                    message = {
                        **message,
                        "headers": [
                            (name, value)
                            for name, value in message.get("headers", ())
                            if name.lower() not in {b"content-length", b"transfer-encoding"}
                        ],
                    }
            elif message["type"] == "http.response.body" and bodyless:
                message = {**message, "body": b""}
            await send(message)

        await self.app(scope, receive, protocol_send)
