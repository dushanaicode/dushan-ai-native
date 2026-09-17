from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class PostSimpleRespVO(BaseVO):
    """管理后台 - 岗位精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr | None, Field(..., description="岗位序号")]
    name: Annotated[str, Field(..., description="岗位名称")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "name": "渡山"}]}}
