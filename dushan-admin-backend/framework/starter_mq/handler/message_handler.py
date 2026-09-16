from abc import ABC, abstractmethod

from pydantic import BaseModel

from framework.starter_mq.model.message_context import MessageContext


class MessageHandler(ABC):
    @abstractmethod
    async def handle(self, message: BaseModel, context: MessageContext) -> None:
        """一次尝试。复杂副作用通过业务事务幂等或 Protection 明确保护。"""
