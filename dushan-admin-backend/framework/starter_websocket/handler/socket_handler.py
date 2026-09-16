from abc import ABC, abstractmethod


class SocketHandler(ABC):
    @abstractmethod
    async def handle(self, payload, context):
        """每条消息独立实例与 DI/Security/Tenant/DP 作用域。"""
