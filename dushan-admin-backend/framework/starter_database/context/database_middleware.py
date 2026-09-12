from starlette.types import ASGIApp, Receive, Scope, Send


class DatabaseMiddleware:
    """把路由粘滞与审计值绑定到完整 HTTP/WebSocket 响应，不隐式开启事务。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        database = scope["app"].state.database
        if database is None:
            await self.app(scope, receive, send)
            return
        with database.scope():
            await self.app(scope, receive, send)
