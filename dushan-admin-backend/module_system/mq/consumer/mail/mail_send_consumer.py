from framework.starter_di.public import (
    Inject,
)
from framework.starter_mq.public import (
    ConsumerDefinition,
    ExhaustedPolicy,
    MessageHandler,
    MessageMode,
    RetryPolicy,
    TenantPolicy,
    consumer,
)
from framework.starter_web.public import (
    RoutePolicy,
)
from module_system.mq.message.mail.mail_send_message import MailSendMessage
from module_system.service.mail.mail_send_service import MailSendService


@consumer(
    ConsumerDefinition(
        key="system.mail.send",
        destination="mail:send",
        mode=MessageMode.STREAM,
        message=MailSendMessage,
        group="mail-consumers",
        retry=RetryPolicy(count=3, delay_seconds=1, backoff=2, max_delay_seconds=30),
        exhausted=ExhaustedPolicy.DEAD_LETTER,
        tenant_policy=TenantPolicy.REQUIRED,
        session_policy=RoutePolicy(tenant_required=True),
        workload_capabilities=frozenset({"system.mail.send"}),
    )
)
class MailSendConsumer(MessageHandler):
    mail_send_service: MailSendService = Inject()

    async def handle(self, message: MailSendMessage, context) -> None:
        await self.mail_send_service.do_send_mail(message)
