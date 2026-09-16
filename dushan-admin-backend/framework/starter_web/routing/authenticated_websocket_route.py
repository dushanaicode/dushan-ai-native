from fastapi import WebSocket
from fastapi.routing import APIWebSocketRoute

from framework.starter_web.routing.route_policy import RoutePolicy


class AuthenticatedWebSocketRoute(APIWebSocketRoute):
    """宿主认证适配器负责握手，不把 WebSocket 伪装成公开 HTTP 路由。"""

    def __init__(self, path, endpoint, *, authorizer, policy: RoutePolicy, name=None):
        if not policy.requires_identity or not callable(authorizer):
            raise ValueError("WebSocket 必须声明独立认证适配器和受保护策略")
        self.authorizer = authorizer

        async def guarded(websocket: WebSocket):
            await authorizer(websocket, endpoint)

        policy(guarded)
        super().__init__(path, guarded, name=name)
