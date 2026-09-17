from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.length import Length
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull


class UserUpdatePasswordReqVO(BaseRequestVO):
    """管理后台 - 用户密码更新 Request VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="用户编号")]
    password: Annotated[str, Field(..., description="密码")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "password": "123456"}]}}

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="用户编号不能为空")
        return v

    @field_validator("password", mode="before")
    @classmethod
    def _validate_password_not_empty_length(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="password", value=v, error_msg="密码不能为空")
        Length.require_length(
            field_name="password",
            value=v,
            min_length=4,
            max_length=16,
            error_msg="密码长度为 4-16 位",
        )
        return v
