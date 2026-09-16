from dataclasses import dataclass

from framework.starter_mq.enums.message_mode import MessageMode
from framework.starter_mq.enums.mq_backend import MQBackend


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    modes: frozenset[MessageMode]
    acknowledged: bool
    durable_retry: bool
    order: str

    @classmethod
    def for_mode(cls, backend, mode):
        supported = {
            MQBackend.REDIS: {MessageMode.STREAM, MessageMode.PUBSUB},
            MQBackend.RABBITMQ: {MessageMode.QUEUE},
            MQBackend.KAFKA: {MessageMode.TOPIC},
        }[backend]
        if mode not in supported:
            raise ValueError("后端不支持该目的地模式")
        if mode is MessageMode.PUBSUB:
            return cls(frozenset(supported), False, False, "在线连接接收顺序；无持久保证")
        return cls(frozenset(supported), True, True, "单分区或单队列并发 1；重试不保序")
