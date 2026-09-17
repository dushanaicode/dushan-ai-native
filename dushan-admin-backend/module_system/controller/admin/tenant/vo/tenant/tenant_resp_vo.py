from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeCursorStr,
    SnowflakeIdStr,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.not_null import NotNull
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.model.excel_column import ExcelColumn


class TenantRespVO(BaseVO):
    """管理后台 - 租户信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="租户编号"), ExcelColumn(title="租户编号")]
    name: Annotated[str, Field(..., description="租户名"), ExcelColumn(title="租户名")]
    contact_name: Annotated[str, Field(..., description="联系人"), ExcelColumn(title="联系人")]
    contact_mobile: Annotated[
        str | None, Field(None, description="联系手机"), ExcelColumn(title="联系手机")
    ]
    status: Annotated[
        int,
        Field(..., description="租户状态"),
        ExcelColumn(title="状态", converter=EnumConverter(StatusEnum)),
    ]
    websites: Annotated[list[str] | None, Field(None, description="绑定域名列表")]
    package_id: Annotated[SnowflakeCursorStr, Field(..., description="租户套餐编号")]
    expire_time: Annotated[datetime, Field(..., description="过期时间")]
    account_count: Annotated[int, Field(..., description="账号数量")]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "渡山",
                    "contactName": "渡山",
                    "contactMobile": "18888888888",
                    "status": 1,
                    "websites": ["https://www.dushan.cn"],
                    "packageId": 1024,
                    "expireTime": "2020-05-20T05:20:00Z",
                    "accountCount": 1024,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="租户编号不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="租户名不能为空")
        return v

    @field_validator("contact_name", mode="before")
    @classmethod
    def _validate_contact_name_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="contact_name", value=v, error_msg="联系人不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="租户状态不能为空")
        return v

    @field_validator("package_id", mode="before")
    @classmethod
    def _validate_package_id_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="package_id", value=v, error_msg="租户套餐编号不能为空")
        return v

    @field_validator("expire_time", mode="before")
    @classmethod
    def _validate_expire_time_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="expire_time", value=v, error_msg="过期时间不能为空")
        return v

    @field_validator("account_count", mode="before")
    @classmethod
    def _validate_account_count_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="account_count", value=v, error_msg="账号数量不能为空")
        return v

    @field_validator("create_time", mode="before")
    @classmethod
    def _validate_create_time_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="create_time", value=v, error_msg="创建时间不能为空")
        return v
