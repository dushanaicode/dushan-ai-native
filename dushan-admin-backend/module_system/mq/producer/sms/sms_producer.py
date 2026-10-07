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
from module_system.mq.message.sms.sms_send_message import SmsSendMessage
from module_system.mq.producer.sms.sms_producer_protocol import SmsProducerProtocol


@service(interface=SmsProducerProtocol)
class SmsProducer(SmsProducerProtocol):
    mq_service: MQService = Inject()

    @transactional
    async def send_sms_message(self, message: SmsSendMessage) -> None:
        """在事务提交后发布短信消息，由框架选择可信身份。"""
        await self.mq_service.publish_after_commit(
            PublishCommand(
                destination=SmsSendMessage.stream_key,
                mode=MessageMode.STREAM,
                message=message,
                message_id=message.message_id,
                workload_capability="system.sms.send",
            )
        )

    @transactional
    async def send_sms_batch(self, sms_batch: list[SmsSendMessage]) -> None:
        for message in sms_batch:
            await self.send_sms_message(message)
