import asyncio
import json
from typing import Any

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.sms.v20210111 import models, sms_client

from module_system.framework.notification.delivery.delivery_attempt import (
    DeliveryRequestStartedCallback,
)
from module_system.framework.notification.delivery.delivery_definite_failure import (
    DeliveryDefiniteFailure,
)
from module_system.framework.sms.client.abstract_sms_client import AbstractSmsClient
from module_system.framework.sms.enums.sms_template_audit_status_enum import (
    SmsTemplateAuditStatusEnum,
)
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties
from module_system.framework.sms.model.sms_receive_resp_dto import SmsReceiveRespDTO
from module_system.framework.sms.model.sms_send_resp_dto import SmsSendRespDTO
from module_system.framework.sms.model.sms_template_resp_dto import SmsTemplateRespDTO


class TencentSmsClient(AbstractSmsClient):
    """
    腾讯云短信功能实现 - 使用官方SDK

    参考文档：https://cloud.tencent.com/document/product/382/55981
    配置要求：properties.api_key 格式为 "secretId sdkAppId"

    继承 AbstractSmsClient 自动获得并发控制（信号量）
    """

    HOST: str = "sms.tencentcloudapi.com"
    VERSION: str = "2021-01-11"
    REGION: str = "ap-beijing"
    API_CODE_SUCCESS: str = "Ok"
    CLIENT_NETWORK_ERROR_CODE: str = "ClientNetworkError"
    DEFINITE_CONNECTION_ERROR_MARKERS: tuple[str, ...] = (
        "ConnectTimeout",
        "Connection refused",
        "Failed to establish a new connection",
        "NameResolutionError",
        "getaddrinfo failed",
        "No route to host",
        "ProxyError",
        "CERTIFICATE_VERIFY_FAILED",
    )
    INTERNATIONAL_CHINA: int = 0
    RATE_LIMIT_MAX_REQUESTS: int = 200
    RATE_LIMIT_WINDOW_SECONDS: float = 1.0

    def __init__(self, properties: SmsChannelProperties):
        """初始化封装框架短信渠道客户端能力。"""
        super().__init__(properties)
        if not properties.api_secret:
            raise ValueError("api_secret 不能为空")
        self.validate_sdk_app_id(properties)

    @staticmethod
    def validate_sdk_app_id(properties: SmsChannelProperties) -> None:
        """校验框架短信相关数据。"""
        combine_key = properties.api_key.strip()
        if not combine_key:
            raise ValueError("api_key 不能为空")
        parts = combine_key.split(" ")
        if len(parts) != 2:
            raise ValueError("腾讯云短信 api_key 配置格式错误，请配置为 'secretId sdkAppId'")

    def get_sdk_app_id(self) -> str:
        """返回腾讯云短信应用编号。"""
        return self.properties.api_key.split(" ")[1]

    def get_api_key(self) -> str:
        """返回腾讯云短信接口密钥。"""
        return self.properties.api_key.split(" ")[0]

    async def send_sms(
        self,
        send_log_id: int,
        mobile: str,
        api_template_id: str,
        template_params: dict[str, Any],
        *,
        on_request_started: DeliveryRequestStartedCallback,
    ) -> SmsSendRespDTO:
        """使用腾讯云SDK发送短信，通过限流+信号量控制并发"""
        await self._acquire_rate_limit(context=f"send_sms, log_id: {send_log_id}")
        async with self._semaphore:
            try:
                cred = credential.Credential(self.get_api_key(), self.properties.api_secret)
                httpProfile = HttpProfile()
                httpProfile.endpoint = self.HOST
                clientProfile = ClientProfile()
                clientProfile.httpProfile = httpProfile
                client = sms_client.SmsClient(cred, self.REGION, clientProfile)
                req = models.SendSmsRequest()
                params = {
                    "PhoneNumberSet": [mobile],
                    "SmsSdkAppId": self.get_sdk_app_id(),
                    "SignName": self.properties.signature,
                    "TemplateId": api_template_id,
                    "TemplateParamSet": [str(value) for value in template_params.values()],
                    "SessionContext": str(send_log_id),
                }
                req.from_json_string(json.dumps(params))
                await on_request_started()
                resp = await asyncio.to_thread(client.SendSms, req)
                if resp.SendStatusSet and len(resp.SendStatusSet) > 0:
                    send_status = resp.SendStatusSet[0]
                    return SmsSendRespDTO(
                        success=send_status.Code == self.API_CODE_SUCCESS,
                        serial_no=send_status.SerialNo,
                        api_request_id=resp.RequestId,
                        api_code=send_status.Code,
                        api_msg=send_status.Message,
                    )
                raise RuntimeError("腾讯云短信响应缺少 SendStatusSet")
            except TencentCloudSDKException as err:
                if self._is_definite_sdk_failure(err):
                    raise DeliveryDefiniteFailure(str(err)) from err
                raise

    @classmethod
    def _is_definite_sdk_failure(cls, error: TencentCloudSDKException) -> bool:
        """区分明确 API/建连失败与可能已提交后的网络中断。"""
        if error.get_code() != cls.CLIENT_NETWORK_ERROR_CODE:
            return True
        message = error.get_message() or ""
        return any((marker in message for marker in cls.DEFINITE_CONNECTION_ERROR_MARKERS))

    async def parse_sms_receive_status(self, text: str) -> list[SmsReceiveRespDTO]:
        """解析短信回执状态"""
        data = json.loads(text)
        result = []
        for item in data:
            dto = SmsReceiveRespDTO(
                success=item.get("report_status") == "SUCCESS",
                error_code=item.get("errmsg"),
                mobile=item.get("mobile"),
                receive_time=item.get("user_receive_time"),
                serial_no=item.get("sid"),
            )
            result.append(dto)
        return result

    async def get_sms_template(self, api_template_id: str) -> SmsTemplateRespDTO:
        """查询短信模板(使用SDK实现)，通过限流+信号量控制并发"""
        await self._acquire_rate_limit(context=f"get_sms_template, template_id: {api_template_id}")
        async with self._semaphore:
            try:
                cred = credential.Credential(self.get_api_key(), self.properties.api_secret)
                httpProfile = HttpProfile()
                httpProfile.endpoint = self.HOST
                clientProfile = ClientProfile()
                clientProfile.httpProfile = httpProfile
                client = sms_client.SmsClient(cred, self.REGION, clientProfile)
                req = models.DescribeSmsTemplateListRequest()
                params = {
                    "International": self.INTERNATIONAL_CHINA,
                    "TemplateIdSet": [int(api_template_id)],
                }
                req.from_json_string(json.dumps(params))
                resp = await asyncio.to_thread(client.DescribeSmsTemplateList, req)
                if not resp.DescribeTemplateStatusSet or len(resp.DescribeTemplateStatusSet) == 0:
                    raise ValueError("未查询到模板状态")
                template_info = resp.DescribeTemplateStatusSet[0]
                return SmsTemplateRespDTO(
                    id=api_template_id,
                    content=template_info.TemplateContent,
                    audit_status=self.convert_sms_template_audit_status(template_info.StatusCode),
                    audit_reason=template_info.ReviewReply,
                )
            except TencentCloudSDKException as err:
                raise ValueError(f"查询短信模板失败: {err}")

    @staticmethod
    def convert_sms_template_audit_status(template_status: int) -> int:
        """转换模板审核状态"""
        if template_status == 1:
            return SmsTemplateAuditStatusEnum.CHECKING.code
        elif template_status == 0:
            return SmsTemplateAuditStatusEnum.SUCCESS.code
        elif template_status == -1:
            return SmsTemplateAuditStatusEnum.FAIL.code
        else:
            raise ValueError(f"未知审核状态({template_status})")
