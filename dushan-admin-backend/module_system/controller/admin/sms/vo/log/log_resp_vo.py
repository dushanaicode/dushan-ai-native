from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import SnowflakeIdStr
from framework.common.enums import UserTypeEnum
from framework.common.schemas import BaseVO
from framework.common.validator import NotNull
from framework.starter_excel.public import (
    EnumConverter,
    ExcelColumn,
    JsonConverter,
)
from module_system.definitions.enums.sms.sms_receive_status_enum import SmsReceiveStatusEnum
from module_system.definitions.enums.sms.sms_send_status_enum import SmsSendStatusEnum
from module_system.definitions.enums.sms.sms_template_type_enum import SmsTemplateTypeEnum


class SmsLogRespVO(BaseVO):
    """管理后台 - 短信日志信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号"), ExcelColumn(title="编号")]
    channel_id: Annotated[
        SnowflakeIdStr, Field(..., description="短信渠道编号"), ExcelColumn(title="短信渠道编号")
    ]
    channel_code: Annotated[
        str, Field(..., description="短信渠道编码"), ExcelColumn(title="短信渠道编码")
    ]
    template_id: Annotated[
        SnowflakeIdStr, Field(..., description="模板编号"), ExcelColumn(title="模板编号")
    ]
    template_code: Annotated[str, Field(..., description="模板编码"), ExcelColumn(title="模板编码")]
    template_type: Annotated[
        int,
        Field(..., description="短信类型"),
        ExcelColumn(title="短信类型", converter=EnumConverter(SmsTemplateTypeEnum)),
    ]
    template_content: Annotated[
        str, Field(..., description="短信内容"), ExcelColumn(title="短信内容")
    ]
    template_params: Annotated[
        dict[str, Any],
        Field(..., description="短信参数"),
        ExcelColumn(title="短信参数", converter=JsonConverter()),
    ]
    api_template_id: Annotated[
        str, Field(..., description="短信 API 的模板编号"), ExcelColumn(title="短信 API 的模板编号")
    ]
    mobile: Annotated[str, Field(..., description="手机号"), ExcelColumn(title="手机号")]
    user_id: Annotated[
        SnowflakeIdStr | None, Field(None, description="用户编号"), ExcelColumn(title="用户编号")
    ]
    user_type: Annotated[
        int | None,
        Field(None, description="用户类型"),
        ExcelColumn(title="用户类型", converter=EnumConverter(UserTypeEnum)),
    ]
    send_status: Annotated[
        int,
        Field(..., description="发送状态"),
        ExcelColumn(title="发送状态", converter=EnumConverter(SmsSendStatusEnum)),
    ]
    send_time: Annotated[
        datetime | None, Field(None, description="发送时间"), ExcelColumn(title="发送时间")
    ]
    api_send_code: Annotated[
        str | None,
        Field(None, description="短信 API 发送结果的编码"),
        ExcelColumn(title="短信 API 发送结果的编码"),
    ]
    api_send_msg: Annotated[
        str | None,
        Field(None, description="短信 API 发送失败的提示"),
        ExcelColumn(title="短信 API 发送失败的提示"),
    ]
    api_request_id: Annotated[
        str | None,
        Field(None, description="短信 API 发送返回的唯一请求 ID"),
        ExcelColumn(title="短信 API 发送返回的唯一请求 ID"),
    ]
    api_serial_no: Annotated[
        str | None,
        Field(None, description="短信 API 发送返回的序号"),
        ExcelColumn(title="短信 API 发送返回的序号"),
    ]
    receive_status: Annotated[
        int,
        Field(..., description="接收状态"),
        ExcelColumn(title="接收状态", converter=EnumConverter(SmsReceiveStatusEnum)),
    ]
    receive_time: Annotated[
        datetime | None, Field(None, description="接收时间"), ExcelColumn(title="接收时间")
    ]
    api_receive_code: Annotated[
        str | None,
        Field(None, description="API 接收结果的编码"),
        ExcelColumn(title="API 接收结果的编码"),
    ]
    api_receive_msg: Annotated[
        str | None,
        Field(None, description="API 接收结果的说明"),
        ExcelColumn(title="API 接收结果的说明"),
    ]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "channelId": 10,
                    "channelCode": "ALIYUN",
                    "templateId": 20,
                    "templateCode": "test-01",
                    "templateType": 1,
                    "templateContent": "你好，你的验证码是 1024",
                    "templateParams": {"name": "", "code": ""},
                    "apiTemplateId": "SMS_207945135",
                    "mobile": "18888888888",
                    "userId": 10,
                    "userType": 1,
                    "sendStatus": 1,
                    "sendTime": "2020-05-20T05:20:00Z",
                    "apiSendCode": "SUCCESS",
                    "apiSendMsg": "成功",
                    "apiRequestId": "3837C6D3-B96F-428C-BBB2-86135D4B5B99",
                    "apiSerialNo": "62923244790",
                    "receiveStatus": 0,
                    "receiveTime": "2020-05-20T05:20:00Z",
                    "apiReceiveCode": "DELIVRD",
                    "apiReceiveMsg": "用户接收成功",
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="id", value=v, error_msg="编号不能为空")
        return v

    @field_validator("channel_id", mode="before")
    @classmethod
    def _validate_channel_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="channel_id", value=v, error_msg="短信渠道编号不能为空")
        return v

    @field_validator("channel_code", mode="before")
    @classmethod
    def _validate_channel_code(cls, v: str) -> str:
        NotNull.require_not_null(
            field_name="channel_code", value=v, error_msg="短信渠道编码不能为空"
        )
        return v

    @field_validator("template_id", mode="before")
    @classmethod
    def _validate_template_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="template_id", value=v, error_msg="模板编号不能为空")
        return v

    @field_validator("template_code", mode="before")
    @classmethod
    def _validate_template_code(cls, v: str) -> str:
        NotNull.require_not_null(field_name="template_code", value=v, error_msg="模板编码不能为空")
        return v

    @field_validator("template_type", mode="before")
    @classmethod
    def _validate_template_type(cls, v: int) -> int:
        NotNull.require_not_null(field_name="template_type", value=v, error_msg="短信类型不能为空")
        return v

    @field_validator("template_content", mode="before")
    @classmethod
    def _validate_template_content(cls, v: str) -> str:
        NotNull.require_not_null(
            field_name="template_content", value=v, error_msg="短信内容不能为空"
        )
        return v

    @field_validator("template_params", mode="before")
    @classmethod
    def _validate_template_params(cls, v: dict[str, Any]) -> dict[str, Any]:
        NotNull.require_not_null(
            field_name="template_params", value=v, error_msg="短信参数不能为空"
        )
        return v

    @field_validator("api_template_id", mode="before")
    @classmethod
    def _validate_api_template_id(cls, v: str) -> str:
        NotNull.require_not_null(
            field_name="api_template_id", value=v, error_msg="短信 API 的模板编号不能为空"
        )
        return v

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile(cls, v: str) -> str:
        NotNull.require_not_null(field_name="mobile", value=v, error_msg="手机号不能为空")
        return v

    @field_validator("send_status", mode="before")
    @classmethod
    def _validate_send_status(cls, v: int) -> int:
        NotNull.require_not_null(field_name="send_status", value=v, error_msg="发送状态不能为空")
        return v

    @field_validator("receive_status", mode="before")
    @classmethod
    def _validate_receive_status(cls, v: int) -> int:
        NotNull.require_not_null(field_name="receive_status", value=v, error_msg="接收状态不能为空")
        return v

    @field_validator("create_time", mode="before")
    @classmethod
    def _validate_create_time(cls, v: datetime) -> datetime:
        NotNull.require_not_null(field_name="create_time", value=v, error_msg="创建时间不能为空")
        return v
