from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_serializer

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from module_system.framework.social.security.social_auth_config_security import (
    SocialAuthConfigSecurity,
)


class SocialClientRespVO(BaseVO):
    """管理后台 - 社交客户端信息 Response VO"""

    id: Annotated[SnowflakeIdStr | None, Field(None, description="编号")]
    name: Annotated[str | None, Field(None, description="应用名")]
    social_type: Annotated[int | None, Field(None, description="社交平台的类型")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    client_id: Annotated[str | None, Field(None, description="客户端编号")]
    client_secret: Annotated[str | None, Field(None, description="客户端密钥", exclude=True)]
    agent_id: Annotated[str | None, Field(None, description="授权方的网页应用编号")]
    auth_config: Annotated[dict[str, Any] | None, Field(None, description="认证配置")]
    status: Annotated[int | None, Field(None, description="状态")]
    create_time: Annotated[datetime | None, Field(None, description="创建时间")]

    @field_serializer("auth_config")
    def public_auth_config(self, value):
        return None if value is None else SocialAuthConfigSecurity.sanitize_auth_config(value)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "dushan商城",
                    "socialType": 31,
                    "userType": 2,
                    "clientId": "wwd411c69a39ad2e54",
                    "clientSecret": "peter",
                    "agentId": "2000045",
                    "authConfig": {
                        "redirectUri": "https://www.example.com/callback",
                        "loginType": "CorpApp",
                        "pkce": False,
                        "unionId": False,
                        "ignoreCheckState": False,
                        "lang": "zh",
                    },
                    "status": 1,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
