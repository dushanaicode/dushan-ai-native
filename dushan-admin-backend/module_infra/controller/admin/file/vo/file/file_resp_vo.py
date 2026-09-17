from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class FileRespVO(BaseVO):
    """管理后台 - 文件信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="文件编号")]
    config_id: Annotated[SnowflakeIdStr, Field(..., description="配置编号")]
    path: Annotated[str, Field(..., description="文件路径")]
    name: Annotated[str, Field(..., description="原文件名")]
    url: Annotated[str, Field(..., description="文件 URL")]
    type: Annotated[str | None, Field(None, description="文件MIME类型")]
    size: Annotated[int, Field(..., description="文件大小")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "configId": 11,
                    "path": "dushan.jpg",
                    "name": "dushan.jpg",
                    "url": "https://www.dushan.info/dushan.jpg",
                    "type": "application/octet-stream",
                    "size": 2048,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
