from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeCursorStr,
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class DeptSimpleRespVO(BaseVO):
    """管理后台 - 部门精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr | None, Field(..., description="部门编号")]
    name: Annotated[str | None, Field(..., description="部门名称")]
    parent_id: Annotated[SnowflakeCursorStr | None, Field(..., description="父部门 ID")]
    model_config = {
        "json_schema_extra": {"examples": [{"id": 1024, "name": "渡山", "parentId": 1024}]}
    }
