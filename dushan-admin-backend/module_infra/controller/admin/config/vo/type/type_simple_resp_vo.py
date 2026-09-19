from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class ConfigTypeSimpleRespVO(BaseVO):
    """管理后台 - 配置类型精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr | None, Field(None, description="配置类型编号")]
    module: Annotated[str, Field(..., description="所属模块标识")]
    name: Annotated[str, Field(..., description="配置类型名称")]
    code: Annotated[str, Field(..., description="配置类型编码")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"id": 1024, "module": "system", "name": "系统配置", "code": "system_config"}
            ]
        }
    }
