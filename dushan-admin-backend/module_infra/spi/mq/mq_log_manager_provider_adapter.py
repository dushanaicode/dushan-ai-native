from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_mq.spi.consume_record_provider import ConsumeRecordProvider
from module_infra.service.mq.mq_log_service import MqLogService


@service(interface=ConsumeRecordProvider)
class MqLogManagerProviderAdapter(ConsumeRecordProvider):
    store: MqLogService = Inject()

    async def append(self, record):
        return await self.store.record(record)
