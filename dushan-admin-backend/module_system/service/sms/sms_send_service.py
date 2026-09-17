from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.mq.message.sms.sms_send_message import SmsSendMessage
from module_system.service.sms.bo.sms_dispatch_bo import SmsDispatchBO
from module_system.service.sms.bo.sms_send_bo import SmsSendBO


@runtime_checkable
class SmsSendService(Protocol):
    async def send_single_sms_to_admin(self, req: SmsSendBO) -> int: ...

    async def send_single_sms(self, req: SmsDispatchBO) -> int: ...

    async def do_send_sms(self, message: SmsSendMessage) -> None: ...

    async def send_single_sms_to_member(self, req: SmsSendBO): ...

    async def receive_sms_status(self, channel_code: str, text: str): ...
