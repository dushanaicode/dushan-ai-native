from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class DataSourceConfigSimpleRespVO(BaseVO):
    """管理后台 - 数据源配置精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="数据源配置编号")]
    name: Annotated[str, Field(..., description="数据源名称")]
    source_type: Annotated[int, Field(..., description="数据源类型")]
    db_type: Annotated[str, Field(..., description="数据库类型")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1, "name": "主数据库", "sourceType": 1, "dbType": "mysql"}]
        }
    }
