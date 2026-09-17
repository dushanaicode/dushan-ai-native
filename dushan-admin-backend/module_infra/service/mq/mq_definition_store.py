from sqlalchemy import select

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_mq.model.consumer_override import ConsumerOverride
from module_infra.dal.dataobject.mq.mq_do import MqDO
from module_infra.dal.mapper.mq.mq_definition_mapper import MqDefinitionMapper


@service
class MqDefinitionStore:
    mapper: MqDefinitionMapper = Inject()

    async def load_overrides(self):
        rows = (await self.mapper.read_from_primary(select(MqDO))).scalars().all()
        return {
            row.consumer: ConsumerOverride(
                enabled=row.enabled, concurrency=row.concurrency, prefetch=row.prefetch
            )
            for row in rows
        }
