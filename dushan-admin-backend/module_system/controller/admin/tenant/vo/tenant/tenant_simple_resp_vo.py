from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.common.validator import NotNull


class TenantSimpleRespVO(BaseVO):
    """管理后台 - 租户精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="租户编号")]
    name: Annotated[str, Field(..., description="租户名")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "name": "渡山"}]}}

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
