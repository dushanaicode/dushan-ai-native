from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class SmsTemplateSimpleRespVO(BaseVO):
    """管理后台 - 短信模板精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="模板编号")]
    code: Annotated[str, Field(..., description="模板编码")]
    name: Annotated[str, Field(..., description="模板名称")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1024, "code": "system-notice", "name": "系统通知"}]
        }
    }
