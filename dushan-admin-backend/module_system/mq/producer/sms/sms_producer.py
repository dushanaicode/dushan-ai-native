from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    MessageMode,
    MQService,
    PublishCommand,
)
from framework.starter_security.public import (
    SecurityService,
)
from module_system.mq.message.sms.sms_send_message import SmsSendMessage
from module_system.mq.producer.sms.sms_producer_protocol import SmsProducerProtocol


@service(interface=SmsProducerProtocol)
class SmsProducer(SmsProducerProtocol):
    security: SecurityService = Inject()
    mq_service: MQService = Inject()

    @transactional
    async def send_sms_message(self, message: SmsSendMessage) -> None:
        await self.mq_service.publish_after_commit(
            PublishCommand(
                destination="sms:send",
                mode=MessageMode.STREAM,
                message=message,
                message_id=message.message_id,
                capability="system.sms.send"
                if self.security.context.current_workload() is not None
                else None,
            )
        )

    @transactional
    async def send_sms_batch(self, sms_batch: list[SmsSendMessage]) -> None:
        for message in sms_batch:
            await self.send_sms_message(message)
