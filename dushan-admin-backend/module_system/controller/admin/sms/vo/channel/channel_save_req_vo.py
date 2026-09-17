from typing import Annotated

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_null import NotNull
from framework.common.validator.url import URL
from module_system.framework.sms.enums.sms_channel_enum import SmsChannelEnum


class SmsChannelSaveReqVO(BaseRequestVO):
    """管理后台 - 短信渠道创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="编号")]
    signature: Annotated[str, Field(..., min_length=1, max_length=12, description="短信签名")]
    code: Annotated[str, Field(..., description="渠道编码，参见 SmsChannelEnum 枚举类")]
    status: Annotated[int, Field(..., description="启用状态")]
    remark: Annotated[str | None, Field(None, description="备注")]
    api_key: Annotated[str, Field(..., description="短信 API 的账号")]
    api_secret: Annotated[str | None, Field(None, description="短信 API 的密钥")]
    callback_url: Annotated[str | None, Field(None, description="短信发送回调 URL")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "1024",
                    "signature": "渡山源码",
                    "code": "ALIYUN",
                    "status": 1,
                    "remark": "fastapi 是最好用的 web 框架",
                    "apiKey": "dushan",
                    "apiSecret": "secret",
                    "callbackUrl": "http://www.dushan.info",
                }
            ]
        }
    }

    @field_validator("signature", mode="before")
    @classmethod
    def _validate_signature(cls, v: str) -> str:
        NotNull.require_not_null(field_name="signature", value=v, error_msg="短信签名不能为空")
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

    @field_validator("callback_url", mode="before")
    @classmethod
    def _validate_callback_url(cls, v: str | None) -> str | None:
        if v is not None and v.strip() != "":
            URL.require_url(field_name="callback_url", value=v, error_msg="回调 URL 格式不正确")
        return v
