import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

import httpx

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


class QiniuSmsClient(AbstractSmsClient):
    """
    七牛云短信客户端

    继承 AbstractSmsClient 自动获得连接池复用、并发控制、重试机制。
    """

    HOST: str = "sms.qiniuapi.com"
    RATE_LIMIT_MAX_REQUESTS: int = 200
    RATE_LIMIT_WINDOW_SECONDS: float = 1.0

    def __init__(self, properties: SmsChannelProperties):
        """初始化封装框架短信渠道客户端能力。"""
        super().__init__(properties)
        if not properties.api_key:
            raise ValueError("api_key (AccessKey) 不能为空")
        if not properties.api_secret:
            raise ValueError("api_secret (SecretKey) 不能为空")

    def _build_qiniu_string_to_sign(
        self,
        method: str,
        path: str,
        host_value: str,
        content_type_value: str | None,
        qiniu_date_header_value: str | None,
        body_for_sign: str,
    ) -> str:
        parts = [method.upper(), " ", path, "\nHost: ", host_value]
        if content_type_value:
            parts.extend(["\nContent-Type: ", content_type_value])
        if qiniu_date_header_value:
            parts.extend(["\nX-Qiniu-Date: ", qiniu_date_header_value])
        parts.append("\n\n")
        if (
            body_for_sign
            and content_type_value
            and (
                "application/json" in content_type_value.lower()
                or "application/x-www-form-urlencoded" in content_type_value.lower()
            )
        ):
            parts.append(body_for_sign)
        return "".join(parts)

    def _calculate_qiniu_signature(self, string_to_sign: str) -> str:
        """计算七牛云短信请求签名。"""
        hmac_digest = hmac.new(
            self.properties.api_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1
        ).digest()
        signature_urlsafe_b64_bytes = base64.urlsafe_b64encode(hmac_digest)
        signature_urlsafe_b64_str = signature_urlsafe_b64_bytes.decode("utf-8").rstrip("=")
        return signature_urlsafe_b64_str

    def get_authorization_header(
        self,
        method: str,
        path: str,
        content_type_value: str | None,
        qiniu_date_header_value: str | None,
        body_json_str: str,
    ) -> str:
        """生成七牛云短信 Authorization 请求头。"""
        string_to_sign = self._build_qiniu_string_to_sign(
            method, path, self.HOST, content_type_value, qiniu_date_header_value, body_json_str
        )
        url_safe_b64_signature = self._calculate_qiniu_signature(string_to_sign)
        return f"Qiniu {self.properties.api_key}:{url_safe_b64_signature}"

    async def request(
        self,
        http_method: str,
        body_dict: dict[str, Any] | None,
        path: str,
        *,
        on_request_started: DeliveryRequestStartedCallback | None = None,
    ) -> dict[str, Any]:
        """通过 execute_with_retry 发起七牛 API 请求。"""
        url, headers, body_json_str = self._build_request_context(http_method, body_dict, path)

        async def do_request():
            """发起当前短信渠道的 HTTP 请求。"""
            return await self._execute_request(http_method, url, headers, body_json_str)

        try:
            response = await self.execute_with_retry(
                do_request, context=f"path={path}", on_request_started=on_request_started
            )
            response_text = response.text
            response.raise_for_status()
            return json.loads(response_text)
        except httpx.HTTPStatusError as http_err:
            return self._build_http_error_payload(http_err)
        except json.JSONDecodeError as json_err:
            raise ValueError("API响应成功但不是有效的JSON") from json_err

    def _build_request_context(
        self, http_method: str, body_dict: dict[str, Any] | None, path: str
    ) -> tuple[str, dict[str, str], str]:
        """构建七牛云请求地址、请求头和正文。"""
        now_utc = datetime.now(timezone.utc)
        qiniu_date_header_value = now_utc.strftime("%Y%m%dT%H%M%SZ")
        body_json_str_for_send = ""
        content_type_header_value = ""
        if http_method.upper() == "POST" and body_dict:
            content_type_header_value = "application/json"
            body_json_str_for_send = json.dumps(body_dict, sort_keys=True, separators=(",", ":"))
        authorization = self.get_authorization_header(
            method=http_method,
            path=path,
            content_type_value=content_type_header_value,
            qiniu_date_header_value=qiniu_date_header_value,
            body_json_str=body_json_str_for_send,
        )
        final_headers = {
            "Host": self.HOST,
            "Authorization": authorization,
            "X-Qiniu-Date": qiniu_date_header_value,
        }
        if content_type_header_value:
            final_headers["Content-Type"] = content_type_header_value
        return (f"https://{self.HOST}{path}", final_headers, body_json_str_for_send)

    async def _execute_request(
        self, http_method: str, url: str, headers: dict[str, str], body_json_str: str
    ):
        """按 HTTP 方法执行七牛云短信请求。"""
        if http_method.upper() == "POST":
            return await self.http_client.post(
                url, headers=headers, content=body_json_str.encode("utf-8")
            )
        if http_method.upper() == "GET":
            return await self.http_client.get(url, headers=headers)
        raise NotImplementedError(f"HTTP method {http_method} not implemented.")

    @staticmethod
    def _build_http_error_payload(http_err: httpx.HTTPStatusError) -> dict[str, Any]:
        """将七牛云 HTTP 错误响应转换为字典。"""
        try:
            error_payload = json.loads(http_err.response.text)
        except json.JSONDecodeError:
            error_payload = {"_raw_error_response_": http_err.response.text}
        if "error" not in error_payload:
            error_payload["error"] = f"HTTP_{http_err.response.status_code}"
        if "message" not in error_payload:
            error_payload["message"] = http_err.response.text
        error_payload["_http_status_code_"] = http_err.response.status_code
        return error_payload

    async def send_sms(
        self,
        send_log_id: int,
        mobile: str,
        api_template_id: str,
        template_params: dict[str, Any],
        *,
        on_request_started: DeliveryRequestStartedCallback,
    ) -> SmsSendRespDTO:
        """发送框架短信相关消息。"""
        path = "/v1/message/single"
        validated_template_params = {k: str(v) for k, v in template_params.items()}
        body_payload: dict[str, Any] = {
            "template_id": api_template_id,
            "mobile": mobile,
            "parameters": validated_template_params,
        }
        if self.properties.signature:
            body_payload["signature_id"] = self.properties.signature
        if send_log_id:
            body_payload["seq"] = str(send_log_id)
        raw_response = await self.request(
            "POST", body_payload, path, on_request_started=on_request_started
        )
        qiniu_error_code = raw_response.get("error")
        qiniu_error_message = raw_response.get("message")
        qiniu_request_id = raw_response.get("request_id")
        if qiniu_error_code:
            return SmsSendRespDTO(
                success=False,
                api_code=str(qiniu_error_code),
                api_request_id=qiniu_request_id,
                api_msg=qiniu_error_message,
            )
        if "message_id" not in raw_response or not raw_response["message_id"]:
            raise RuntimeError("七牛云短信响应缺少 message_id")
        message_id_from_qiniu = raw_response["message_id"]
        return SmsSendRespDTO(
            success=True,
            serial_no=message_id_from_qiniu,
            api_request_id=qiniu_request_id,
            api_code="SUCCESS",
            api_msg="短信已提交发送",
        )

    async def get_sms_template(self, api_template_id: str) -> SmsTemplateRespDTO:
        """查询七牛云短信模板详情。"""
        path = f"/v1/template/{api_template_id}"
        response = await self.request("GET", None, path)
        if response.get("error"):
            qiniu_error_code = response.get("error")
            qiniu_error_message = response.get("message")
            raise Exception(f"查询七牛模板失败: {qiniu_error_message} (Code: {qiniu_error_code})")
        return SmsTemplateRespDTO(
            id=str(response.get("id")),
            content=str(response.get("template")),
            audit_status=self.convert_sms_template_audit_status(response.get("audit_status")),
            audit_reason=response.get("reject_reason"),
        )

    @staticmethod
    def convert_sms_template_audit_status(qiniu_template_status: str | None) -> int:
        """转换框架短信相关数据结构。"""
        status_str = str(qiniu_template_status).lower()
        if status_str == "passed":
            return SmsTemplateAuditStatusEnum.SUCCESS.code
        elif status_str == "reviewing":
            return SmsTemplateAuditStatusEnum.CHECKING.code
        elif status_str == "rejected":
            return SmsTemplateAuditStatusEnum.FAIL.code
        else:
            return SmsTemplateAuditStatusEnum.CHECKING.code

    async def parse_sms_receive_status(self, text: str) -> list[SmsReceiveRespDTO]:
        """解析框架短信相关文本或标识。"""
        try:
            data_payload = json.loads(text)
            items_to_parse = data_payload if isinstance(data_payload, list) else [data_payload]
        except json.JSONDecodeError:
            return []
        result_dtos: list[SmsReceiveRespDTO] = []
        for item in items_to_parse:
            if not isinstance(item, dict):
                continue
            serial_no = item.get("message_id")
            mobile_num = item.get("mobile")
            status_qiniu = item.get("status")
            error_code_qiniu = item.get("err_code")
            description_qiniu = item.get("description")
            report_time_str = item.get("report_time")
            log_id_str = item.get("user_data")
            is_success = str(status_qiniu).upper() == "DELIVRD"
            receive_time_obj: datetime | None = None
            if report_time_str:
                try:
                    dt_naive = datetime.strptime(report_time_str, "%Y-%m-%d %H:%M:%S")
                    receive_time_obj = dt_naive.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            log_id_val: int | None = None
            if log_id_str:
                try:
                    log_id_val = int(log_id_str)
                except ValueError:
                    pass
            result_dtos.append(
                SmsReceiveRespDTO(
                    success=is_success,
                    error_code=str(error_code_qiniu) if error_code_qiniu else status_qiniu,
                    error_msg=description_qiniu,
                    mobile=mobile_num,
                    receive_time=receive_time_obj,
                    serial_no=serial_no,
                    log_id=log_id_val,
                )
            )
        return result_dtos
