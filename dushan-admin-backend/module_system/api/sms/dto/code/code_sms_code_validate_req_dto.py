from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_dto import BaseDTO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.mobile import Mobile
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from module_system.definitions.enums.sms.sms_scene_enum import SmsSceneEnum


class SmsCodeValidateReqDTO(BaseDTO):
    """短信验证码的校验 Request DTO"""

    mobile: Annotated[str | None, Field(default=None, description="手机号")]
    scene: Annotated[int | None, Field(default=None, description="发送场景")]
    code: Annotated[str | None, Field(default=None, description="验证码")]

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="mobile", value=v, error_msg="手机号不能为空")
        return Mobile.require_mobile(field_name="mobile", value=v, error_msg="手机号格式不正确")

    @field_validator("scene", mode="before")
    @classmethod
    def _validate_scene(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="scene", value=v, error_msg="发送场景不能为空")
        return InEnum.require_in_enum(
            field_name="scene",
            value=v,
            enum_class=SmsSceneEnum,
            error_msg="发送场景必须是指定范围内",
        )

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(field_name="code", value=v, error_msg="验证码不能为空")
