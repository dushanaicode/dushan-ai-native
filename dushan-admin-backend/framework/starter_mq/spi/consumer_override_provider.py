from typing import Protocol

from framework.starter_mq.model.consumer_override import ConsumerOverride


class ConsumerOverrideProvider(Protocol):
    async def load(self) -> dict[str, ConsumerOverride]:
        """可选部署覆盖，启动时读取；不得引入新的消费者或修改业务定义。"""
        ...
