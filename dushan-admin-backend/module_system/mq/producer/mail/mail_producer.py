from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_mq.core.mq_service import MQService
from framework.starter_mq.enums.message_mode import MessageMode
from framework.starter_mq.model.publish_command import PublishCommand
from framework.starter_security.core.security_service import SecurityService
from module_system.mq.message.mail.mail_send_message import MailSendMessage
from module_system.mq.producer.mail.mail_producer_protocol import MailProducerProtocol


@service(interface=MailProducerProtocol)
class MailProducer(MailProducerProtocol):
    security: SecurityService = Inject()
    mq_service: MQService = Inject()

    @transactional
    async def send_mail_message(self, message: MailSendMessage) -> None:
        await self.mq_service.publish_after_commit(
            PublishCommand(
                destination="mail:send",
                mode=MessageMode.STREAM,
                message=message,
                message_id=message.message_id,
                capability="system.mail.send"
                if self.security.context.current_workload() is not None
                else None,
            )
        )

    @transactional
    async def send_mail_batch(self, mail_batch: list[MailSendMessage]) -> None:
        for message in mail_batch:
            await self.send_mail_message(message)
