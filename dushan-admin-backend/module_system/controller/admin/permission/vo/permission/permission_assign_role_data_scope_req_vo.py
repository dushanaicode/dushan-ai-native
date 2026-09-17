from typing import Annotated

from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from module_system.definitions.enums.permission.permission_data_scope_enum import (
    PermissionDataScopeEnum,
)


class PermissionAssignRoleDataScopeReqVO(BaseRequestVO):
    """管理后台 - 分配角色数据权限 Request VO"""

    role_id: Annotated[SnowflakeIdInput, Field(..., title="角色编号", description="角色编号")]
    data_scope: Annotated[
        int, Field(..., title="数据范围", description="数据范围, 枚举值见 PermissionDataScopeEnum")
    ]
    data_scope_dept_ids: Annotated[
        set[SnowflakeIdInput] | None,
        Field(
            default=None,
            title="部门编号列表",
            description="部门编号列表，适用于DATA_SCOPE_DEPT_CUSTOM类型的数据权限",
        ),
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [{"roleId": 1, "dataScope": 1, "dataScopeDeptIds": [10, 20, 30]}]
        }
    }

    @field_validator("role_id", mode="before")
    @classmethod
    def _validate_role_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="role_id", value=v, error_msg="角色编号不能为空")
        return v

    @field_validator("data_scope", mode="before")
    @classmethod
    def _validate_data_scope(cls, v: int) -> int:
        NotNull.require_not_null(field_name="data_scope", value=v, error_msg="数据范围不能为空")
        InEnum.require_in_enum(
            field_name="data_scope",
            value=v,
            enum_class=PermissionDataScopeEnum,
            error_msg="数据范围必须是",
        )
        return v

    @field_validator("data_scope_dept_ids", mode="before")
    @classmethod
    def _validate_data_scope_dept_ids(
        cls, v: set[int] | None, info: ValidationInfo
    ) -> set[int] | None:
        data_scope_value_from_input = info.data.get("data_scope")
        expected_data_scope_code = PermissionDataScopeEnum.DEPT_CUSTOM.code
        actual_data_scope_matches = False
        if data_scope_value_from_input is not None:
            try:
                if int(data_scope_value_from_input) == expected_data_scope_code:
                    actual_data_scope_matches = True
            except (ValueError, TypeError):
                NotEmpty.require_not_empty(
                    field_name="data_scope_dept_ids",
                    value=v,
                    error_msg="部门编号列表不能为空，当数据范围为 DEPT_CUSTOM 时",
                )
        if actual_data_scope_matches:
            NotEmpty.require_not_empty(
                field_name="data_scope_dept_ids",
                value=v,
                error_msg="部门编号列表不能为空，当数据范围为 DEPT_CUSTOM 时",
            )
        return v
