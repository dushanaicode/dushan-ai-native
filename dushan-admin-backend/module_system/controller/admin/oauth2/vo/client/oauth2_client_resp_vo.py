from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class OAuth2ClientRespVO(BaseVO):
    """管理后台 - OAuth2 客户端信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号")]
    client_id: Annotated[str, Field(..., description="客户端编号")]
    secret: Annotated[str, Field(..., description="客户端密钥", exclude=True)]
    name: Annotated[str, Field(..., description="应用名")]
    logo: Annotated[str, Field(..., description="应用图标")]
    description: Annotated[str | None, Field(None, description="应用描述")]
    status: Annotated[int, Field(..., description="状态，参见 StatusEnum 枚举")]
    access_token_validity_seconds: Annotated[int, Field(..., description="访问令牌的有效期")]
    refresh_token_validity_seconds: Annotated[int, Field(..., description="刷新令牌的有效期")]
    redirect_uris: Annotated[list[str], Field(..., description="可重定向的 URI 地址")]
    authorized_grant_types: Annotated[
        list[str], Field(..., description="授权类型，参见 OAuth2GrantTypeEnum 枚举")
    ]
    scopes: Annotated[list[str] | None, Field(None, description="授权范围")]
    auto_approve_scopes: Annotated[list[str] | None, Field(None, description="自动通过的授权范围")]
    authorities: Annotated[list[str] | None, Field(None, description="权限")]
    resource_ids: Annotated[list[str] | None, Field(None, description="资源")]
    additional_information: Annotated[str | None, Field(None, description="附加信息 (对象格式)")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "clientId": "dushan",
                    "secret": "fan",
                    "name": "渡山",
                    "logo": "https://www.dushan.info/xx.png",
                    "description": "我是一个应用",
                    "status": 1,
                    "accessTokenValiditySeconds": 8640,
                    "refreshTokenValiditySeconds": 8640000,
                    "redirectUris": ["https://www.dushan.info"],
                    "authorizedGrantTypes": ["password"],
                    "scopes": ["user_info"],
                    "autoApproveScopes": ["user_info"],
                    "authorities": ["system:user:query"],
                    "resourceIds": ["1024"],
                    "additionalInformation": None,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("additional_information", mode="before")
    @classmethod
    def additional_info_empty_str_to_none(cls, v: Any) -> Any:
        """在验证前，将空字符串 "" 转换成 None"""
        if v == "":
            return None
        return v
