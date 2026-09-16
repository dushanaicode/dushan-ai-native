from contextlib import AbstractAsyncContextManager
from typing import Protocol

from framework.starter_mq.model.message_context import MessageContext


class MessageInterceptor(Protocol):
    def enter(self, context: MessageContext) -> AbstractAsyncContextManager[None]:
        """认证与租户准入之后进入，每次按声明顺序进入、逆序清理。"""
        ...
