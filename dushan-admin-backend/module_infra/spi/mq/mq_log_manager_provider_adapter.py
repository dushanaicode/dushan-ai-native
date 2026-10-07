from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    ConsumeRecord,
    ConsumeRecordProvider,
)
from module_infra.service.mq.mq_log_service import MqLogService


@service(interface=ConsumeRecordProvider)
class MqLogManagerProviderAdapter(ConsumeRecordProvider):
    store: MqLogService = Inject()

    @override
    async def append(self, record: ConsumeRecord) -> None:
        return await self.store.record(record)
