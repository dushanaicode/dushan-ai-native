from abc import abstractmethod

from framework.starter_websocket.public import (
    SocketHandler,
)
from module_infra.framework.websocket.infra_socket_payload import InfraSocketPayload


class SystemMessageHandlerBase(SocketHandler):
    async def handle(self, payload, context):
        value = await self.process_message()
        await context.reply(self.response_type, InfraSocketPayload(data=value))

    @abstractmethod
    async def process_message(self): ...
