from typing import Any, ClassVar

from pydantic import Field, field_validator

from framework.common.schemas.base_bo import BaseBO
from framework.common.validator.not_null import NotNull


class SmsSendMessage(BaseBO):
    """
    短信发送消息的数据模型
    """

    message_id: str = Field(..., description="消息唯一ID")
    log_id: int = Field(..., description="短信日志编号")
    mobile: str = Field(..., description="手机号")
    channel_id: int = Field(..., description="短信渠道编号")
    api_template_id: str = Field(..., description="短信 API 的模板编号")
    template_params: dict[str, Any] = Field(
        default_factory=dict, description="短信模板参数 (字典形式)"
    )
    stream_key: ClassVar[str] = "sms:send"

    @field_validator("log_id", mode="before")
    @classmethod
    def _validate_log_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="log_id", value=v, error_msg="短信日志编号不能为空")
        return v

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile(cls, v: str) -> str:
        NotNull.require_not_null(field_name="mobile", value=v, error_msg="手机号不能为空")
        return v

    @field_validator("channel_id", mode="before")
    @classmethod
    def _validate_channel_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="channel_id", value=v, error_msg="短信渠道编号不能为空")
        return v

    @field_validator("api_template_id", mode="before")
    @classmethod
    def _validate_api_template_id(cls, v: str) -> str:
        NotNull.require_not_null(
            field_name="api_template_id", value=v, error_msg="短信 API 的模板编号不能为空"
        )
        return v
