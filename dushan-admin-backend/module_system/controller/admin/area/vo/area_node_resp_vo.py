from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class AreaNodeRespVO(BaseVO):
    """管理后台 - 地区节点 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号")]
    name: Annotated[str, Field(..., description="名字")]
    children: Annotated[list["AreaNodeRespVO"] | None, Field(None, description="子节点")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 110000,
                    "name": "北京",
                    "children": [{"id": 110100, "name": "北京市", "children": None}],
                }
            ]
        }
    }
