from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.enums import StatusEnum, UserTypeEnum
from framework.common.schemas import BaseRequestVO
from framework.common.validator import InEnum, NotNull
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum


class SocialClientSaveReqVO(BaseRequestVO):
    """管理后台 - 社交客户端创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="编号")]
    name: Annotated[str, Field(..., description="应用名")]
    social_type: Annotated[int, Field(..., description="社交平台的类型")]
    user_type: Annotated[int, Field(..., description="用户类型")]
    client_id: Annotated[str, Field(..., description="客户端编号")]
    client_secret: Annotated[str, Field(..., description="客户端密钥")]
    agent_id: Annotated[str | None, Field(None, description="授权方的网页应用编号")]
    auth_config: Annotated[dict[str, Any] | None, Field(None, description="认证配置")]
    status: Annotated[int, Field(..., description="状态")]
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
                    },
                    "status": 1,
                }
            ]
        }
    }

    @model_validator(mode="after")
    def validate_agent_id(self):
        """验证企业微信应用时agent_id不能为空"""
        if self.social_type == SocialTypeEnum.WECHAT_ENTERPRISE.code:
            if not self.agent_id or self.agent_id.strip() == "":
                raise ValueError("agentId 不能为空")
        return self

    @field_validator("name", mode="before")
    @classmethod
    def require_name(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="应用名不能为空")
        return v

    @field_validator("social_type", mode="before")
    @classmethod
    def require_social_type_enum(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="social_type", value=v, error_msg="社交平台的类型不能为空"
        )
        InEnum.require_in_enum(
            field_name="social_type",
            value=v,
            enum_class=SocialTypeEnum,
            error_msg="社交平台的类型必须在指定范围",
        )
        return v

    @field_validator("user_type", mode="before")
    @classmethod
    def require_user_type_enum(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="user_type", value=v, error_msg="用户类型不能为空")
        InEnum.require_in_enum(
            field_name="user_type",
            value=v,
            enum_class=UserTypeEnum,
            error_msg="用户类型必须在指定范围",
        )
        return v

    @field_validator("client_id", mode="before")
    @classmethod
    def require_client_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="client_id", value=v, error_msg="客户端编号不能为空")
        return v

    @field_validator("client_secret", mode="before")
    @classmethod
    def require_client_secret(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="client_secret", value=v, error_msg="客户端密钥不能为空"
        )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def require_status_enum(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="状态必须在指定范围"
        )
        return v
