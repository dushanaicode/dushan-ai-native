from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.common.validator import URL, InEnum, NotNull
from module_system.framework.sms.enums.sms_channel_enum import SmsChannelEnum


class SmsChannelRespVO(BaseVO):
    """管理后台 - 短信渠道信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号")]
    signature: Annotated[str, Field(..., description="短信签名")]
    code: Annotated[str, Field(..., description="渠道编码，参见 SmsChannelEnum 枚举类")]
    status: Annotated[int, Field(..., description="启用状态")]
    remark: Annotated[str | None, Field(None, description="备注")]
    api_key: Annotated[str, Field(..., description="短信 API 的账号", exclude=True)]
    api_secret: Annotated[str | None, Field(None, description="短信 API 的密钥", exclude=True)]
    callback_url: Annotated[str | None, Field(None, description="短信发送回调 URL")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "signature": "渡山源码",
                    "code": "YUN_PIAN",
                    "status": 1,
                    "remark": "好吃！",
                    "apiKey": "dushan",
                    "apiSecret": "yuanma",
                    "callbackUrl": "https://www.dushan.info",
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

    @field_validator("signature", mode="before")
    @classmethod
    def _validate_signature(cls, v: str) -> str:
        NotNull.require_not_null(field_name="signature", value=v, error_msg="短信签名不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: int) -> int:
        NotNull.require_not_null(field_name="status", value=v, error_msg="启用状态不能为空")
        return v

    @field_validator("api_key", mode="before")
    @classmethod
    def _validate_api_key(cls, v: str) -> str:
        NotNull.require_not_null(field_name="api_key", value=v, error_msg="短信 API 的账号不能为空")
        return v

    @field_validator("create_time", mode="before")
    @classmethod
    def _validate_create_time(cls, v: datetime) -> datetime:
        NotNull.require_not_null(field_name="create_time", value=v, error_msg="创建时间不能为空")
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        InEnum.require_in_enum(
            field_name="code",
            value=v,
            enum_class=SmsChannelEnum,
            error_msg="渠道编码必须在指定范围 {value}",
        )
        return v

    @field_validator("callback_url", mode="before")
    @classmethod
    def _validate_callback_url(cls, v: str | None) -> str | None:
        if v is not None and v.strip() != "":
            URL.require_url(field_name="callback_url", value=v, error_msg="回调 URL 格式不正确")
        return v
