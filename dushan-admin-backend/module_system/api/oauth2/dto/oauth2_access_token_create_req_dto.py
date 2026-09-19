from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.enums import UserTypeEnum
from framework.common.schemas import BaseDTO
from framework.common.validator import InEnum, NotNull


class OAuth2AccessTokenCreateReqDTO(BaseDTO):
    """OAuth2.0 访问令牌创建 Request DTO"""

    user_id: Annotated[int | None, Field(description="用户编号")]
    user_type: Annotated[int | None, Field(description="用户类型")]
    client_id: Annotated[str | None, Field(description="客户端编号")]
    scopes: Annotated[list[str] | None, Field(description="授权范围")]

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
            error_msg="用户类型必须是在指定范围内",
        )

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="client_id", value=v, error_msg="客户端编号不能为空"
        )
