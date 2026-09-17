from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class UserSimpleRespVO(BaseVO):
    """管理后台 - 用户精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="用户编号")]
    nickname: Annotated[str, Field(..., description="用户昵称")]
    dept_id: Annotated[SnowflakeIdStr | None, Field(None, description="部门ID")]
    dept_name: Annotated[str | None, Field(None, description="部门名称")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1024, "nickname": "渡山", "deptId": 1024, "deptName": "IT 部"}]
        }
    }
