from typing import Annotated

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.common.validator import NotEmpty, NotNull


class RoleSimpleRespVO(BaseVO):
    """管理后台 - 角色精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="角色编号")]
    name: Annotated[str, Field(..., description="角色名称")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "name": "渡山"}]}}

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="id", value=v, error_msg="角色编号不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="角色名称不能为空")
        return v
