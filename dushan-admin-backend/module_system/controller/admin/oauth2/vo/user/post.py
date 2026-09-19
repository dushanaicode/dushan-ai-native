from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.common.validator import NotEmpty, NotNull


class Post(BaseVO):
    """管理后台 - OAuth2 用户岗位信息 VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="岗位编号")]
    name: Annotated[str, Field(..., description="岗位名称")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1, "name": "开发"}]}}

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="岗位编号不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="岗位名称不能为空")
        return v
