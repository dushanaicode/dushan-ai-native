from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.page.schemas.page_query import PageQuery
from framework.common.validator.in_enum import InEnum


class UserPageReqVO(PageQuery):
    """管理后台 - 用户分页列表 Request VO"""

    username: Annotated[str | None, Field(None, description="用户账号，模糊匹配")]
    mobile: Annotated[str | None, Field(None, description="手机号码，模糊匹配")]
    status: Annotated[int | None, Field(None, description="展示状态，参见 StatusEnum 枚举类")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    dept_id: Annotated[SnowflakeIdInput | None, Field(None, description="部门编号，同时筛选子部门")]
    role_id: Annotated[SnowflakeIdInput | None, Field(None, description="角色编号")]
    fields: Annotated[list[str] | None, Field(None, description="导出的字段列表")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "dushan",
                    "mobile": "18888888888",
                    "status": 1,
                    "createTime": ["2020-05-20T05:20:00Z", "2022-07-01T23:59:59Z"],
                    "deptId": 1024,
                    "roleId": 1024,
                    "pageNo": 1,
                    "pageSize": 10,
                    "fields": ["username", "mobile", "status", "createTime"],
                }
            ]
        }
    }

    @field_validator("status", mode="after")
    @classmethod
    def _validate_status_in_enum(cls, v: int | None) -> int | None:
        if v is not None:
            InEnum.require_in_enum(
                field_name="status",
                value=v,
                enum_class=StatusEnum,
                error_msg="状态必须在指定范围内",
            )
        return v
