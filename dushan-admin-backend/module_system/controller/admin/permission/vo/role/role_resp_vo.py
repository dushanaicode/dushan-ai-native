from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.not_blank import NotBlank
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.converter.ids_converter import IdsConverter
from framework.starter_excel.model.excel_column import ExcelColumn
from module_system.definitions.enums.permission.permission_data_scope_enum import (
    PermissionDataScopeEnum,
)


class RoleRespVO(BaseVO):
    """管理后台 - 角色信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="角色编号"), ExcelColumn(title="角色序号")]
    name: Annotated[str, Field(..., description="角色名称"), ExcelColumn(title="角色名称")]
    code: Annotated[str, Field(..., description="角色标志"), ExcelColumn(title="角色标志")]
    sort: Annotated[int, Field(..., description="显示顺序"), ExcelColumn(title="角色排序")]
    status: Annotated[
        int,
        Field(..., description="状态"),
        ExcelColumn(title="角色状态", converter=EnumConverter(StatusEnum)),
    ]
    builtin: Annotated[int, Field(..., description="内置类型，参见 BuiltinTypeEnum")]
    remark: Annotated[str | None, Field(None, description="备注")]
    data_scope: Annotated[
        int,
        Field(..., description="数据范围"),
        ExcelColumn(title="数据范围", converter=EnumConverter(PermissionDataScopeEnum)),
    ]
    data_scope_dept_ids: Annotated[
        list[SnowflakeIdStr] | None,
        Field(None, description="数据范围(指定部门数组)"),
        ExcelColumn(title="指定部门", converter=IdsConverter("departments")),
    ]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "管理员",
                    "code": "admin",
                    "sort": 1024,
                    "status": 0,
                    "type": 1,
                    "remark": "我是一个角色",
                    "dataScope": 1,
                    "dataScopeDeptIds": [1],
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        NotBlank.require_not_blank(field_name="code", value=v, error_msg="角色标志不能为空")
        return v
