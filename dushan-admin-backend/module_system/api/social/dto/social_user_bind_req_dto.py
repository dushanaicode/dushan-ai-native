from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.enums import UserTypeEnum
from framework.common.schemas import BaseDTO
from framework.common.validator import InEnum, NotEmpty, NotNull
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum


class SocialUserBindReqDTO(BaseDTO):
    """社交用户绑定 Request DTO"""

    user_id: Annotated[int | None, Field(default=None, description="用户编号")]
    user_type: Annotated[int | None, Field(default=None, description="用户类型")]
    type: Annotated[int | None, Field(default=None, description="社交平台的类型")]
    code: Annotated[str | None, Field(default=None, description="授权码")]
    state: Annotated[str | None, Field(default=None, description="state")]

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, v: Any) -> Any:
        return NotNull.require_not_null(field_name="user_id", value=v, error_msg="用户编号不能为空")

    @field_validator("user_type", mode="before")
    @classmethod
    def _validate_user_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="user_type", value=v, error_msg="用户类型不能为空")
        return InEnum.require_in_enum(
            field_name="user_type",
            value=v,
            enum_class=UserTypeEnum,
            error_msg="用户类型必须是指定范围内",
        )

    @field_validator("type", mode="before")
    @classmethod
    def _validate_social_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="type", value=v, error_msg="社交平台类型不能为空")
        return InEnum.require_in_enum(
            field_name="type",
            value=v,
            enum_class=SocialTypeEnum,
            error_msg="社交平台类型必须是指定范围内",
        )

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(field_name="code", value=v, error_msg="授权码不能为空")

    @field_validator("state", mode="before")
    @classmethod
    def _validate_state(cls, v: Any) -> Any:
        return NotNull.require_not_null(field_name="state", value=v, error_msg="state 不能为空")
