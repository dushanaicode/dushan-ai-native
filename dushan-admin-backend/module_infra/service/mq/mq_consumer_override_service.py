from typing import Protocol, runtime_checkable

from framework.starter_mq.public import ConsumerOverride


@runtime_checkable
class MqConsumerOverrideService(Protocol):
    """读取管理端维护的消费者覆盖配置，交给 MQ 运行时。"""

    async def load_overrides(self) -> dict[str, ConsumerOverride]: ...
