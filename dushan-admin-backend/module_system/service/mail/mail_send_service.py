from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.mq.message.mail.mail_send_message import MailSendMessage
from module_system.service.mail.bo.mail_batch_dispatch_bo import MailBatchDispatchBO
from module_system.service.mail.bo.mail_batch_send_bo import MailBatchSendBO
from module_system.service.mail.bo.mail_dispatch_bo import MailDispatchBO
from module_system.service.mail.bo.mail_send_bo import MailSendBO


@runtime_checkable
class MailSendService(Protocol):
    async def send_single_mail_to_admin(self, req: MailSendBO) -> int: ...

    async def send_single_mail_to_member(self, req: MailSendBO) -> int: ...

    async def send_multiple_mail_to_admin(self, req: MailBatchSendBO) -> int: ...

    async def send_multiple_mail_to_member(self, req: MailBatchSendBO) -> int: ...

    async def send_single_mail(self, req: MailDispatchBO) -> int: ...

    async def send_multiple_mail(self, req: MailBatchDispatchBO) -> int: ...

    async def do_send_mail(self, message: MailSendMessage) -> None: ...
