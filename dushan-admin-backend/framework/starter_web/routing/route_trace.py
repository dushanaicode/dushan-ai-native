from starlette.types import ASGIApp, Receive, Scope, Send


class RouteTrace:
    """为原生 Starlette Route/Mount 保存已匹配模板，不读取原始 URL。"""

    def __init__(self, app: ASGIApp, path: str) -> None:
        self.app = app
        self.path = path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope.setdefault("state", {})["web_route_template"] = self.path
        await self.app(scope, receive, send)
