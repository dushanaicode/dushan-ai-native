from dataclasses import dataclass

from framework.starter_mq.definitions.enums.message_mode import MessageMode
from framework.starter_mq.definitions.enums.mq_backend import MQBackend


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    acknowledged: bool

    @classmethod
    def for_mode(cls, backend, mode):
        supported = {
            MQBackend.REDIS: {MessageMode.STREAM, MessageMode.PUBSUB},
            MQBackend.RABBITMQ: {MessageMode.QUEUE},
            MQBackend.KAFKA: {MessageMode.TOPIC},
        }[backend]
        if mode not in supported:
            raise ValueError("后端不支持该目的地模式")
        return cls(mode is not MessageMode.PUBSUB)
