from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.common.validator import NotEmpty, NotNull


class Dept(BaseVO):
    """管理后台 - OAuth2 用户部门信息 VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="部门编号")]
    name: Annotated[str, Field(..., description="部门名称")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1, "name": "研发部"}]}}

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="部门编号不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="部门名称不能为空")
        return v
