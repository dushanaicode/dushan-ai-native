from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.enums import StatusEnum
from framework.common.schemas import BaseRequestVO
from framework.common.validator import InEnum, NotEmpty, NotNull
from module_system.controller.admin.tenant.vo.packages.packages_package_quota_config_vo import (
    TenantPackageQuotaConfigVO,
)


class TenantPackageSaveReqVO(BaseRequestVO):
    """管理后台 - 租户套餐创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="套餐编号")]
    name: Annotated[str, Field(..., description="套餐名")]
    status: Annotated[int, Field(..., description="状态，参见 StatusEnum 枚举")]
    remark: Annotated[str | None, Field(None, description="备注")]
    menu_ids: Annotated[list[SnowflakeIdInput] | None, Field(None, description="关联的菜单编号")]
    quota_config: Annotated[
        TenantPackageQuotaConfigVO | None,
        Field(None, description="通用配额模板（多模块共享，如 ai / sms / storage）"),
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "VIP",
                    "status": 0,
                    "remark": "备注",
                    "menuIds": [1, 2, 3, 4, 5],
                    "quotaConfig": {
                        "ai": {
                            "enabled": True,
                            "billingMode": 3,
                            "monthlyTokenLimit": 500000,
                            "monthlyAmountLimit": 100.0,
                            "dailyTokenLimit": -1,
                        }
                    },
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name_not_empty(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="套餐名不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status_not_null_in_enum(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="状态必须是 {value}"
        )
        return v

    @field_validator("menu_ids", mode="before")
    @classmethod
    def _validate_menu_ids_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="menu_ids", value=v, error_msg="关联的菜单编号不能为空")
        return v
