from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class OAuth2AccessTokenSchema(BaseRequestVO):
    """管理后台 - OAuth2 访问令牌 Schema"""

    id: Annotated[SnowflakeIdInput, Field(..., description="编号")]
    user_id: Annotated[SnowflakeIdInput, Field(..., description="用户编号")]
    user_type: Annotated[int, Field(..., description="用户类型")]
    user_info: Annotated[str, Field(..., description="用户信息")]
    access_token: Annotated[str, Field(..., description="访问令牌")]
    refresh_token: Annotated[str, Field(..., description="刷新令牌")]
    client_id: Annotated[str, Field(..., description="客户端编号")]
    scopes: Annotated[list[str] | None, Field(None, description="授权范围")]
    expires_time: Annotated[datetime, Field(..., description="过期时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "userId": 2048,
                    "userType": 2,
                    "userInfo": '{"id":2048,"username":"admin"}',
                    "accessToken": "e5d142bf-3394-4f29-a947-7d2c52e517fc",
                    "refreshToken": "8bdfe96e-5119-4263-a492-7d2c52e517fc",
                    "clientId": "default",
                    "scopes": ["user.read", "user.write"],
                    "expiresTime": "2023-01-01T12:00:00Z",
                }
            ]
        }
    }
