from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_null import NotNull


class PermissionAssignRoleMenuReqVO(BaseRequestVO):
    """管理后台 - 分配角色菜单 Request VO"""

    role_id: Annotated[SnowflakeIdInput, Field(..., description="角色编号")]
    menu_ids: Annotated[
        set[SnowflakeIdInput], Field(default_factory=set, description="菜单编号列表")
    ]
    model_config = {"json_schema_extra": {"examples": [{"roleId": 1, "menuIds": [1, 3, 5]}]}}

    @field_validator("role_id", mode="before")
    @classmethod
    def _validate_role_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="role_id", value=v, error_msg="角色编号不能为空")
        return v
