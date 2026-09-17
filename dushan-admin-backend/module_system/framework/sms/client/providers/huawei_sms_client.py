import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, quote

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


class HuaweiSmsClient(AbstractSmsClient):
    """
    华为短信客户端的实现类
    """

    URL = "https://smsapi.cn-north-4.myhuaweicloud.com:443/sms/batchSendSms/v1"
    HOST = "smsapi.cn-north-4.myhuaweicloud.com:443"
    SIGNED_HEADERS = "content-type;host;x-sdk-date"
    RESPONSE_CODE_SUCCESS = "000000"
    RATE_LIMIT_MAX_REQUESTS: int = 200
    RATE_LIMIT_WINDOW_SECONDS: float = 1.0

    def __init__(self, properties: SmsChannelProperties):
        """初始化封装框架短信渠道客户端能力。"""
        super().__init__(properties)
        if not properties.api_key:
            raise ValueError("api_key 不能为空")
        if not properties.api_secret:
            raise ValueError("api_secret 不能为空")
        self.validate_sender(properties)

    @staticmethod
    def validate_sender(properties: SmsChannelProperties) -> None:
        """校验 api_key 配置格式为 "accessKeyId sender" """
        combine_key = properties.api_key.strip()
        if not combine_key:
            raise ValueError("api_key 不能为空")
        parts = combine_key.split(" ")
        if len(parts) != 2:
            raise ValueError("华为云短信 api_key 配置格式错误，请配置为 'accessKeyId sender'")

    def get_access_key(self) -> str:
        """返回华为云短信访问密钥。"""
        return self.properties.api_key.split(" ")[0]

    def get_sender(self) -> str:
        """返回华为云短信发送方标识。"""
        return self.properties.api_key.split(" ")[1]

    @staticmethod
    def percent_code(s: str) -> str:
        """按华为云签名规则进行百分号编码。"""
        encoded = quote(s, safe="")
        return encoded.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def append_to_body(body: list[str], key: str, value: str) -> None:
        """将华为云签名参数追加到请求体。"""
        if value:
            body.append(f"{key}{quote(value, encoding='utf-8')}")

    async def send_sms(
        self,
        send_log_id: int,
        mobile: str,
        api_template_id: str,
        template_params: dict[str, Any],
        *,
        on_request_started: DeliveryRequestStartedCallback,
    ) -> SmsSendRespDTO:
        """发送短信"""
        body_parts = []
        HuaweiSmsClient.append_to_body(body_parts, "from=", self.get_sender())
        HuaweiSmsClient.append_to_body(body_parts, "&to=", mobile)
        HuaweiSmsClient.append_to_body(body_parts, "&templateId=", api_template_id)
        param_values_for_huawei = [str(value) for value in template_params.values()]
        template_paras_json_array = json.dumps(param_values_for_huawei, ensure_ascii=False)
        HuaweiSmsClient.append_to_body(body_parts, "&templateParas=", template_paras_json_array)
        callback_url = (
            self.properties.callback_url if self.properties.callback_url is not None else ""
        )
        HuaweiSmsClient.append_to_body(body_parts, "&statusCallback=", callback_url)
        HuaweiSmsClient.append_to_body(body_parts, "&extend=", str(send_log_id))
        request_body = "".join(body_parts)
        response = await self.request(
            "/sms/batchSendSms/v1/", "POST", request_body, on_request_started=on_request_started
        )
        response_code = response["code"]
        if response_code != HuaweiSmsClient.RESPONSE_CODE_SUCCESS:
            return SmsSendRespDTO(
                success=False, api_code=response_code, api_msg=response.get("description")
            )
        if "result" not in response:
            raise RuntimeError("华为云短信成功响应缺少 result")
        result_array = response["result"]
        send_result = result_array[0] if result_array else None
        if send_result is None:
            raise RuntimeError("华为云短信成功响应 result 为空")
        return SmsSendRespDTO(
            success=True, serial_no=send_result.get("smsMsgId"), api_code=send_result["status"]
        )

    async def request(
        self,
        uri: str,
        method: str,
        request_body: str,
        *,
        on_request_started: DeliveryRequestStartedCallback | None = None,
    ) -> dict[str, Any]:
        """
        请求华为云短信 API：
          - 构造签名 + Authorization Header
          - 通过 execute_with_retry 发送（自动并发控制 + 重试）
        """
        headers: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}
        sdk_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        headers["X-Sdk-Date"] = sdk_date
        headers["host"] = HuaweiSmsClient.HOST
        canonical_headers = f"content-type:application/x-www-form-urlencoded\nhost:{HuaweiSmsClient.HOST}\nx-sdk-date:{sdk_date}\n"
        canonical_query_string = ""
        canonical_request = (
            method
            + "\n"
            + uri
            + "\n"
            + canonical_query_string
            + "\n"
            + canonical_headers
            + "\n"
            + HuaweiSmsClient.SIGNED_HEADERS
            + "\n"
            + hashlib.sha256(request_body.encode("utf-8")).hexdigest()
        )
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = "SDK-HMAC-SHA256" + "\n" + sdk_date + "\n" + hashed_canonical_request
        signature = hmac.new(
            self.properties.api_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["Authorization"] = (
            f"SDK-HMAC-SHA256 Access={self.get_access_key()}, SignedHeaders={HuaweiSmsClient.SIGNED_HEADERS}, Signature={signature}"
        )

        async def do_request():
            """发起当前短信渠道的 HTTP 请求。"""
            return await self.http_client.post(
                HuaweiSmsClient.URL, headers=headers, content=request_body
            )

        response = await self.execute_with_retry(
            do_request, context=f"uri={uri}", on_request_started=on_request_started
        )
        self.raise_for_definite_http_failure(response)
        return json.loads(response.text)

    async def parse_sms_receive_status(self, request_body: str) -> list[SmsReceiveRespDTO]:
        """解析华为短信回执状态"""
        params = {k: v[0] for k, v in parse_qs(request_body).items()}
        update_time_str = params.get("updateTime")
        try:
            receive_time = (
                datetime.fromisoformat(update_time_str) if update_time_str is not None else None
            )
        except ValueError:
            receive_time = None
        extend = params.get("extend")
        if extend is None:
            raise ValueError("Huawei SMS callback missing extend")
        return [
            SmsReceiveRespDTO(
                success=params.get("status") == "DELIVRD",
                error_code=params.get("status"),
                error_msg=params.get("statusDesc"),
                mobile=params.get("to"),
                receive_time=receive_time,
                serial_no=params.get("smsMsgId"),
                log_id=int(extend),
            )
        ]

    async def get_sms_template(self, api_template_id: str) -> SmsTemplateRespDTO:
        """华为短信模板查询"""
        parts = api_template_id.strip().split(" ")
        if len(parts) != 2:
            raise ValueError("格式不正确，需要满足：apiTemplateId sender")
        return SmsTemplateRespDTO(
            id=api_template_id,
            content=None,
            audit_status=SmsTemplateAuditStatusEnum.SUCCESS.code,
            audit_reason=None,
        )
