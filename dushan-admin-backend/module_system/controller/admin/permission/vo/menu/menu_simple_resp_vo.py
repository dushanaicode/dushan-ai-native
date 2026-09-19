from typing import Annotated, Literal

from pydantic import Field

from framework.common.contracts import (
    SnowflakeCursorStr,
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class MenuSimpleRespVO(BaseVO):
    """管理后台 - 菜单精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="菜单编号")]
    name: Annotated[str, Field(..., description="菜单名称")]
    parent_id: Annotated[SnowflakeCursorStr, Field(..., description="父菜单 ID")]
    kind: Literal["group", "page", "action", "link", "iframe"]
    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1024, "name": "渡山", "parentId": 1024, "type": 1}]
        }
    }
    url: str | None = None
    data_permission: bool = False
