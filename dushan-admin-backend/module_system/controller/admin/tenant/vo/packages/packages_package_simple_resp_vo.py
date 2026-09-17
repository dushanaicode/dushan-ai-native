from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.not_null import NotNull


class TenantPackageSimpleRespVO(BaseVO):
    """管理后台 - 租户套餐精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="套餐编号")]
    name: Annotated[str, Field(..., description="套餐名")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "name": "VIP"}]}}

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
