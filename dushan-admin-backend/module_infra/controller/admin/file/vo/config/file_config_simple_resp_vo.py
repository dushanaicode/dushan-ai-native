from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class FileConfigSimpleRespVO(BaseVO):
    """管理后台 - 文件配置精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号")]
    name: Annotated[str, Field(..., description="配置名")]
    storage: Annotated[int, Field(..., description="存储器")]
    master: Annotated[bool, Field(..., description="是否为主配置")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1, "name": "S3 - 阿里云", "storage": 20, "master": True}]
        }
    }
