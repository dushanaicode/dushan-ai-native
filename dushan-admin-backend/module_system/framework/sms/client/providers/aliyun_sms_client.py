import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from loguru import logger

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


class AliyunSmsClient(AbstractSmsClient):
    """阿里云短信客户端的实现，基于 AbstractSmsClient 抽象基类"""

    URL = "https://dysmsapi.aliyuncs.com"
    HOST = "dysmsapi.aliyuncs.com"
    VERSION = "2017-05-25"
    RESPONSE_CODE_SUCCESS = "OK"
    RATE_LIMIT_MAX_REQUESTS: int = 200
    RATE_LIMIT_WINDOW_SECONDS: float = 1.0

    def __init__(self, properties: SmsChannelProperties):
        """初始化封装框架短信渠道客户端能力。"""
        super().__init__(properties)
        if not properties.api_key:
            raise ValueError("api_key 不能为空")
        if not properties.api_secret:
            raise ValueError("api_secret 不能为空")

    @staticmethod
    def percent_code(s: str) -> str:
        """对字符串进行 URL 编码，并替换部分字符以符合规范"""
        encoded = quote(s, safe="")
        return encoded.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    async def send_sms(
        self,
        send_log_id: int,
        mobile: str,
        api_template_id: str,
        template_params: dict[str, Any],
        *,
        on_request_started: DeliveryRequestStartedCallback,
    ) -> SmsSendRespDTO:
        """发送短信：校验短信签名是否存在，构造请求参数，调用 request 方法发起 HTTP POST 请求，根据响应生成 SmsSendRespDTO 对象"""
        if not self.properties.signature:
            raise ValueError("短信签名不能为空")
        template_param_json_str = JsonUtils().to_json(template_params)
        query_params = {
            "PhoneNumbers": mobile,
            "SignName": self.properties.signature,
            "TemplateCode": api_template_id,
            "TemplateParam": template_param_json_str,
            "OutId": send_log_id,
        }
        response = await self.request(
            "SendSms", query_params, on_request_started=on_request_started
        )
        response_code = response["Code"]
        return SmsSendRespDTO(
            success=response_code == AliyunSmsClient.RESPONSE_CODE_SUCCESS,
            serial_no=response.get("BizId"),
            api_request_id=response.get("RequestId"),
            api_code=response_code,
            api_msg=response.get("Message"),
        )

    async def parse_sms_receive_status(self, text: str) -> list[SmsReceiveRespDTO]:
        """解析短信回执状态"""
        statuses = json.loads(text)
        result = []
        for status in statuses:
            result.append(
                SmsReceiveRespDTO(
                    success=status.get("success"),
                    error_code=status.get("err_code"),
                    error_msg=status.get("err_msg"),
                    mobile=status.get("phone_number"),
                    receive_time=status.get("report_time"),
                    serial_no=status.get("biz_id"),
                    log_id=status.get("out_id"),
                )
            )
        return result

    async def get_sms_template(self, api_template_id: str) -> SmsTemplateRespDTO | None:
        """查询短信模板"""
        query_params = {"TemplateCode": api_template_id}
        response = await self.request("QuerySmsTemplate", query_params)
        code = response.get("Code")
        if code != AliyunSmsClient.RESPONSE_CODE_SUCCESS:
            logger.error(
                "【AliyunSmsClient】模板查询失败：template_id={} code={}", api_template_id, code
            )
            return None
        return SmsTemplateRespDTO(
            id=response.get("TemplateCode"),
            content=response.get("TemplateContent"),
            audit_status=self.convert_sms_template_audit_status(response.get("TemplateStatus")),
            audit_reason=response.get("Reason"),
        )

    @staticmethod
    def convert_sms_template_audit_status(template_status: int) -> int:
        """将短信模板审核状态转换为统一的状态码"""
        if template_status == 0:
            return SmsTemplateAuditStatusEnum.CHECKING.code
        elif template_status == 1:
            return SmsTemplateAuditStatusEnum.SUCCESS.code
        elif template_status == 2:
            return SmsTemplateAuditStatusEnum.FAIL.code
        else:
            raise ValueError(f"未知审核状态({template_status})")

    async def request(
        self,
        api_name: str,
        query_params: dict[str, Any],
        *,
        on_request_started: DeliveryRequestStartedCallback | None = None,
    ) -> dict[str, Any]:
        """发起阿里云短信 API 请求。"""
        query_string = self._build_query_string(query_params)
        headers = self._build_signed_headers(api_name, query_string)
        request_body = ""
        full_url = f"{AliyunSmsClient.URL}?{query_string}"

        async def do_request():
            """发起当前短信渠道的 HTTP 请求。"""
            return await self.http_client.post(full_url, headers=headers, content=request_body)

        response = await self.execute_with_retry(
            do_request, context=f"api={api_name}", on_request_started=on_request_started
        )
        self.raise_for_definite_http_failure(response)
        return json.loads(response.text)

    @staticmethod
    def _build_query_string(query_params: dict[str, Any]) -> str:
        """构建阿里云签名使用的查询字符串。"""
        return "&".join(
            (
                f"{AliyunSmsClient.percent_code(k)}={AliyunSmsClient.percent_code(str(v))}"
                for k, v in sorted(query_params.items())
            )
        )

    def _build_signed_headers(self, api_name: str, query_string: str) -> dict[str, str]:
        """构建阿里云短信请求的签名头集合。"""
        headers = self._build_base_headers(api_name)
        canonical_headers, signed_headers = self._build_canonical_headers(headers)
        canonical_request = self._build_canonical_request(
            query_string, canonical_headers, signed_headers
        )
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = "ACS3-HMAC-SHA256" + "\n" + hashed_canonical_request
        signature = hmac.new(
            self.properties.api_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["Authorization"] = self._build_authorization_header(signed_headers, signature)
        return headers

    @staticmethod
    def _build_base_headers(api_name: str) -> dict[str, str]:
        """构建阿里云短信请求的基础头。"""
        now_utc = datetime.now(timezone.utc)
        return {
            "host": AliyunSmsClient.HOST,
            "x-acs-version": AliyunSmsClient.VERSION,
            "x-acs-action": api_name,
            "x-acs-date": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "x-acs-signature-nonce": IdUtils().simple_uuid(),
        }

    @staticmethod
    def _build_canonical_headers(headers: dict[str, str]) -> tuple[str, str]:
        """构建阿里云签名规范化请求头。"""
        canonical_headers = ""
        signed_headers_list: list[str] = []
        for key in sorted(headers.keys(), key=lambda x: x.lower()):
            lower_key = key.lower()
            if lower_key.startswith("x-acs-") or lower_key in ["host", "content-type"]:
                canonical_headers += f"{lower_key}:{str(headers[key]).strip()}\n"
                signed_headers_list.append(lower_key)
        return (canonical_headers, ";".join(signed_headers_list))

    @staticmethod
    def _build_canonical_request(
        query_string: str, canonical_headers: str, signed_headers: str
    ) -> str:
        """构建阿里云签名规范请求串。"""
        hashed_request_body = hashlib.sha256(b"").hexdigest()
        return (
            "POST"
            + "\n"
            + "/"
            + "\n"
            + query_string
            + "\n"
            + canonical_headers
            + "\n"
            + signed_headers
            + "\n"
            + hashed_request_body
        )

    def _build_authorization_header(self, signed_headers: str, signature: str) -> str:
        """构建阿里云短信 Authorization 请求头。"""
        return f"ACS3-HMAC-SHA256 Credential={self.properties.api_key}, SignedHeaders={signed_headers}, Signature={signature}"
