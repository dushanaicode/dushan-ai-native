from typing import Any, Protocol, runtime_checkable

from module_system.framework.notification.delivery.delivery_attempt import (
    DeliveryRequestStartedCallback,
)
from module_system.framework.sms.model.sms_receive_resp_dto import SmsReceiveRespDTO
from module_system.framework.sms.model.sms_send_resp_dto import SmsSendRespDTO
from module_system.framework.sms.model.sms_template_resp_dto import SmsTemplateRespDTO


@runtime_checkable
class SmsClient(Protocol):
    """短信客户端接口，用于对接各短信平台的 SDK，实现短信发送等功能"""

    def get_id(self) -> int | None:
        """获得渠道编号"""
        ...

    async def send_sms(
        self,
        send_log_id: int,
        mobile: str,
        api_template_id: str,
        template_params: dict[str, Any],
        *,
        on_request_started: DeliveryRequestStartedCallback,
    ) -> SmsSendRespDTO:
        """发送消息"""
        ...

    async def parse_sms_receive_status(self, text: str) -> list[SmsReceiveRespDTO]:
        """解析接收短信的接收结果"""
        ...

    async def get_sms_template(self, api_template_id: str) -> SmsTemplateRespDTO | None:
        """查询指定的短信模板"""
        ...
