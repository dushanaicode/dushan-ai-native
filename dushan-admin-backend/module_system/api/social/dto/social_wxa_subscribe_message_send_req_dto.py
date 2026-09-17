from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_dto import BaseDTO
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull


class SocialWxaSubscribeMessageSendReqDTO(BaseDTO):
    """微信小程序订阅消息发送 Request DTO"""

    user_id: Annotated[int | None, Field(default=None, description="用户编号")]
    user_type: Annotated[int | None, Field(default=None, description="用户类型")]
    template_title: Annotated[str | None, Field(default=None, description="消息模版标题")]
    page: Annotated[str | None, Field(default=None, description="点击模板卡片后的跳转页面")]
    messages: Annotated[dict[str, str] | None, Field(default=None, description="模板内容的参数")]

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, v: Any) -> Any:
        return NotNull.require_not_null(field_name="user_id", value=v, error_msg="用户编号不能为空")

    @field_validator("user_type", mode="before")
    @classmethod
    def _validate_user_type(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="user_type", value=v, error_msg="用户类型不能为空"
        )

    @field_validator("template_title", mode="before")
    @classmethod
    def _validate_template_title(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(
            field_name="template_title", value=v, error_msg="消息模版标题不能为空"
        )
