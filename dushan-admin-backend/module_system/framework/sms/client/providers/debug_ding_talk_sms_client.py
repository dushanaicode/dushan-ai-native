import base64
import hashlib
import hmac
import time
from typing import Any
from urllib.parse import quote

from framework.common.utils import IdUtils, JsonUtils
from module_system.framework.notification.delivery.delivery_attempt import (
    DeliveryRequestStartedCallback,
)
from module_system.framework.sms.client.abstract_sms_client import AbstractSmsClient
from module_system.framework.sms.enums.sms_template_audit_status_enum import (
    SmsTemplateAuditStatusEnum,
)
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties
from module_system.framework.sms.model.sms_receive_resp_dto import SmsReceiveRespDTO
from module_system.framework.sms.model.sms_send_resp_dto import SmsSendRespDTO
from module_system.framework.sms.model.sms_template_resp_dto import SmsTemplateRespDTO


class DebugDingTalkSmsClient(AbstractSmsClient):
    """基于钉钉 WebHook 实现的调试短信客户端"""

    RATE_LIMIT_MAX_REQUESTS: int = 20
    RATE_LIMIT_WINDOW_SECONDS: float = 60.0

    def __init__(self, properties: SmsChannelProperties):
        """初始化封装框架短信渠道客户端能力。"""
        super().__init__(properties)
        if not properties.api_key:
            raise ValueError("api_key 不能为空")
        if not properties.api_secret:
            raise ValueError("api_secret 不能为空")

    async def send_sms(
        self,
        send_log_id: int,
        mobile: str,
        api_template_id: str,
        template_params: dict[str, Any],
        *,
        on_request_started: DeliveryRequestStartedCallback,
    ) -> SmsSendRespDTO:
        """发送短信：构造钉钉消息体，通过 execute_with_retry 发送"""
        template_params_str = JsonUtils().to_json(template_params)
        params_for_dingtalk_body = {
            "msgtype": "text",
            "text": {
                "content": f"【模拟短信】\n手机号：{mobile}\n短信日志编号：{send_log_id}\n模板ID (API)：{api_template_id}\n模板参数：{template_params_str}"
            },
        }
        url = self.build_url("robot/send")

        async def do_request():
            """发起当前短信渠道的 HTTP 请求。"""
            return await self.http_client.post(url, json=params_for_dingtalk_body)

        response = await self.execute_with_retry(
            do_request, context=f"log_id: {send_log_id}", on_request_started=on_request_started
        )
        self.raise_for_definite_http_failure(response)
        response_obj = JsonUtils().parse_obj(response.text, dict)
        error_code = str(response_obj["errcode"])
        raw_error_msg = response_obj.get("errmsg")
        return SmsSendRespDTO(
            success=error_code == "0",
            serial_no=IdUtils().simple_uuid(),
            api_code=error_code,
            api_msg=str(raw_error_msg) if raw_error_msg is not None else None,
        )

    def build_url(self, path: str) -> str:
        """
                构建请求地址

                生成 timestamp 与签名，签名计算规则：
                "{timestamp}
        {secret}"，使用 HMAC-SHA256 算法，并对结果进行 Base64 编码和 URL 编码。
        """
        timestamp = int(time.time() * 1000)
        secret = self.properties.api_secret
        string_to_sign = f"{timestamp}\n{secret}"
        sign_data = hmac.new(
            secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
        ).digest()
        sign = base64.b64encode(sign_data).decode("utf-8")
        encoded_sign = quote(sign)
        return f"https://oapi.dingtalk.com/{path}?access_token={self.properties.api_key}&timestamp={timestamp}&sign={encoded_sign}"

    async def parse_sms_receive_status(self, text: str) -> list[SmsReceiveRespDTO]:
        """解析框架短信相关文本或标识。"""
        raise NotImplementedError("模拟短信客户端，暂时无需解析回调")

    async def get_sms_template(self, api_template_id: str) -> SmsTemplateRespDTO:
        """模拟查询短信模板，审核状态固定为 SUCCESS"""
        return SmsTemplateRespDTO(
            id=api_template_id,
            content="",
            audit_status=SmsTemplateAuditStatusEnum.SUCCESS.code,
            audit_reason="",
        )
