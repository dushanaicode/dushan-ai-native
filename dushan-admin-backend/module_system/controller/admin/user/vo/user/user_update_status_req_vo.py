from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_null import NotNull


class UserUpdateStatusReqVO(BaseRequestVO):
    """管理后台 - 用户状态更新 Request VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="用户编号")]
    status: Annotated[int, Field(..., description="状态，见 StatusEnum 枚举")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "status": 1}]}}

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="用户编号不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status_not_null_in_enum(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="状态必须在指定范围内"
        )
        return v
