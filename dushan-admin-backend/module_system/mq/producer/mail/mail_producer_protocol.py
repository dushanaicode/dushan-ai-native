from typing import Protocol, runtime_checkable

from module_system.mq.message.mail.mail_send_message import MailSendMessage


@runtime_checkable
class MailProducerProtocol(Protocol):
    async def send_mail_message(self, message: MailSendMessage) -> None: ...
    async def send_mail_batch(self, mail_batch: list[MailSendMessage]) -> None: ...
