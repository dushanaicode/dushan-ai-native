from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeCursorStr,
    SnowflakeIdStr,
)
from framework.common.enums import StatusEnum
from framework.common.schemas import BaseVO
from framework.common.validator import InEnum, NotEmpty, NotNull


class DeptRespVO(BaseVO):
    """管理后台 - 部门信息 Response VO"""

    id: Annotated[SnowflakeIdStr | None, Field(None, description="部门编号")]
    name: Annotated[str, Field(..., description="部门名称")]
    parent_id: Annotated[SnowflakeCursorStr | None, Field(None, description="父部门 ID")]
    sort: Annotated[int, Field(..., description="显示顺序")]
    leader_user_id: Annotated[SnowflakeIdStr | None, Field(None, description="负责人的用户编号")]
    phone: Annotated[str | None, Field(None, description="联系电话")]
    email: Annotated[str | None, Field(None, description="邮箱")]
    status: Annotated[int, Field(..., description="状态,见 StatusEnum 枚举")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "渡山",
                    "parentId": 1024,
                    "sort": 1024,
                    "leaderUserId": 2048,
                    "phone": "18888888888",
                    "email": "729227973@qq.com",
                    "status": 1,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="部门名称不能为空")
        return v

    @field_validator("sort", mode="before")
    @classmethod
    def _validate_sort(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="sort", value=v, error_msg="显示顺序不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status",
            value=v,
            enum_class=StatusEnum,
            error_msg="状态必须在指定范围 {values}",
        )
        return v
