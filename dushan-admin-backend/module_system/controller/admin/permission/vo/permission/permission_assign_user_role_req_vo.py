from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_null import NotNull


class PermissionAssignUserRoleReqVO(BaseRequestVO):
    """管理后台 - 用户角色分配 Request VO"""

    user_id: Annotated[SnowflakeIdInput, Field(..., description="用户编号")]
    role_ids: Annotated[
        set[SnowflakeIdInput], Field(default_factory=set, description="角色编号列表")
    ]
    model_config = {"json_schema_extra": {"examples": [{"userId": 1, "roleIds": [1, 3, 5]}]}}

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="user_id", value=v, error_msg="用户编号不能为空")
        return v

    @field_validator("role_ids", mode="before")
    @classmethod
    def _validate_role_ids(cls, v: set[int], values: dict) -> set[int]:
        NotNull.require_not_null(field_name="role_ids", value=v, error_msg="角色编号列表不能为空")
        return v
