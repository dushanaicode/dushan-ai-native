from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseVO


class MemoryInfoVO(BaseVO):
    """管理后台 - 内存信息 VO"""

    total: Annotated[str | None, Field(description="内存总量")] = None
    used: Annotated[str | None, Field(description="已用内存")] = None
    free: Annotated[str | None, Field(description="剩余内存")] = None
    usage: Annotated[float | None, Field(description="使用率")] = None
    model_config = {
        "json_schema_extra": {
            "examples": [{"total": "16GB", "used": "8GB", "free": "8GB", "usage": 50.0}]
        }
    }
