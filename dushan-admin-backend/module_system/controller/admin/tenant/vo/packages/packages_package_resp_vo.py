from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.enums import StatusEnum
from framework.common.schemas import BaseVO
from framework.common.validator import NotNull
from framework.starter_excel.public import (
    EnumConverter,
    ExcelColumn,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_quota_config_vo import (
    TenantPackageQuotaConfigVO,
)


class TenantPackageRespVO(BaseVO):
    """管理后台 - 租户套餐信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="套餐编号"), ExcelColumn(title="套餐编号")]
    name: Annotated[str, Field(..., description="套餐名"), ExcelColumn(title="套餐名")]
    status: Annotated[
        int,
        Field(..., description="状态，参见 StatusEnum 枚举"),
        ExcelColumn(title="状态", converter=EnumConverter(StatusEnum)),
    ]
    remark: Annotated[str | None, Field(None, description="备注"), ExcelColumn(title="备注")]
    menu_ids: Annotated[list[SnowflakeIdStr], Field(..., description="关联的菜单编号")]
    quota_config: Annotated[
        TenantPackageQuotaConfigVO | None, Field(None, description="通用配额模板")
    ]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "VIP",
                    "status": 1,
                    "remark": "备注",
                    "menuIds": [1, 2, 3, 4, 5],
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="套餐编号不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="套餐名不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        return v

    @field_validator("menu_ids", mode="before")
    @classmethod
    def _validate_menu_ids_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="menu_ids", value=v, error_msg="关联的菜单编号不能为空")
        return v
