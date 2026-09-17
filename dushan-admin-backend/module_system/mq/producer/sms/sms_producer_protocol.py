from typing import Protocol, runtime_checkable

from module_system.mq.message.sms.sms_send_message import SmsSendMessage


@runtime_checkable
class SmsProducerProtocol(Protocol):
    async def send_sms_message(self, message: SmsSendMessage) -> None: ...
    async def send_sms_batch(self, sms_batch: list[SmsSendMessage]) -> None: ...
