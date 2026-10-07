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
from module_system.mq.message.mail.mail_send_message import MailSendMessage
from module_system.mq.producer.mail.mail_producer_protocol import MailProducerProtocol


@service(interface=MailProducerProtocol)
class MailProducer(MailProducerProtocol):
    mq_service: MQService = Inject()

    @transactional
    async def send_mail_message(self, message: MailSendMessage) -> None:
        """在事务提交后发布邮件消息，由框架选择可信身份。"""
        await self.mq_service.publish_after_commit(
            PublishCommand(
                destination=MailSendMessage.stream_key,
                mode=MessageMode.STREAM,
                message=message,
                message_id=message.message_id,
                workload_capability="system.mail.send",
            )
        )

    @transactional
    async def send_mail_batch(self, mail_batch: list[MailSendMessage]) -> None:
        for message in mail_batch:
            await self.send_mail_message(message)
