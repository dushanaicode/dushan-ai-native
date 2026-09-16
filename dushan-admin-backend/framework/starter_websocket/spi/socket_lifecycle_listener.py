from typing import Protocol

from framework.starter_websocket.model.online_connection import OnlineConnection


class SocketLifecycleListener(Protocol):
    audience: str

    async def connected(self, connection: OnlineConnection) -> None: ...

    async def disconnected(self, connection: OnlineConnection, code: int) -> None:
        """每个连接只通知一次；不携带已失效的身份上下文。"""
        ...
