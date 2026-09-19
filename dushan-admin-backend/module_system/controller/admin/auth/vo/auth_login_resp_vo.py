from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class AuthLoginRespVO(BaseVO):
    """管理后台 - 登录 Response VO"""

    user_id: Annotated[SnowflakeIdStr, Field(..., description="用户编号")]
    access_token: Annotated[str, Field(..., description="访问令牌")]
    refresh_token: Annotated[str, Field(..., description="刷新令牌", exclude=True)]
    expires_time: Annotated[int, Field(..., description="过期时间的毫秒级时间戳")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userId": 1024,
                    "accessToken": "happy",
                    "refreshToken": "nice",
                    "expiresTime": 1678956123456,
                }
            ]
        }
    }

    refresh_expires_time: int = Field(exclude=True)
