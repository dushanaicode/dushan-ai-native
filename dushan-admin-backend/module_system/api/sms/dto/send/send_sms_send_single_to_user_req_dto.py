from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_dto import BaseDTO
from framework.common.validator.mobile import Mobile
from framework.common.validator.not_empty import NotEmpty


class SmsSendSingleToUserReqDTO(BaseDTO):
    """短信发送给 Admin 或者 Member 用户"""

    user_id: Annotated[int | None, Field(default=None, description="用户编号")]
    mobile: Annotated[str | None, Field(default=None, description="手机号")]
    template_code: Annotated[str | None, Field(default=None, description="短信模板编号")]
    template_params: Annotated[
        dict[str, Any], Field(default_factory=dict, description="短信模板参数")
    ]

    @field_validator("template_code", mode="before")
    @classmethod
    def _validate_template_code(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(
            field_name="template_code", value=v, error_msg="短信模板编号不能为空"
        )

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="mobile", value=v, error_msg="手机号不能为空")
        return Mobile.require_mobile(field_name="mobile", value=v, error_msg="手机号格式不正确")
