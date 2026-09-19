from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class DictTypeSimpleRespVO(BaseVO):
    """管理后台 - 字典类型精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr | None, Field(None, description="字典类型编号")]
    name: Annotated[str, Field(..., description="字典类型名称")]
    type: Annotated[str, Field(..., description="字典类型")]
    model_config = {
        "json_schema_extra": {"examples": [{"id": 1024, "name": "渡山", "type": "sys_common_sex"}]}
    }
