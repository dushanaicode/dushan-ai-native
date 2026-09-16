from abc import ABC, abstractmethod


class MessageBackend(ABC):
    """各后端保留自身确认和流控语义；没有原生单条 nack 的 Kafka 不伪装支持。"""

    @abstractmethod
    async def open(self, definitions): ...

    @abstractmethod
    async def publish(self, destination, mode, body): ...

    @abstractmethod
    def messages(self, definition, prefetch): ...

    @abstractmethod
    async def retry(self, definition, envelope, body): ...

    @abstractmethod
    async def dead_letter(self, definition, body): ...

    @abstractmethod
    async def stop_receiving(self): ...

    @abstractmethod
    async def close(self): ...
