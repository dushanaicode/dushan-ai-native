from typing import override

from sqlalchemy import select

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    ConsumerOverride,
)
from module_infra.dal.dataobject.mq.mq_do import MqDO
from module_infra.dal.mapper.mq.mq_definition_mapper import MqDefinitionMapper
from module_infra.service.mq.mq_consumer_override_service import MqConsumerOverrideService


@service(interface=MqConsumerOverrideService)
class MqConsumerOverrideServiceImpl(MqConsumerOverrideService):
    """把消费者覆盖记录转换为 MQ 运行时覆盖配置。"""

    mapper: MqDefinitionMapper = Inject()

    @override
    async def load_overrides(self):
        rows = (await self.mapper.read_from_primary(select(MqDO))).scalars().all()
        return {
            row.consumer: ConsumerOverride(
                enabled=row.enabled, concurrency=row.concurrency, prefetch=row.prefetch
            )
            for row in rows
        }
