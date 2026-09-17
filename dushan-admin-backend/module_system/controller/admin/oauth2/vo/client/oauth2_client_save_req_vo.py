from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_null import NotNull
from framework.common.validator.url import URL
from module_system.definitions.enums.oauth2.oauth2_grant_type_enum import OAuth2GrantTypeEnum


class OAuth2ClientSaveReqVO(BaseRequestVO):
    """管理后台 - OAuth2 客户端创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="编号")]
    client_id: Annotated[str, Field(..., description="客户端ID")]
    secret: Annotated[str | None, Field(None, description="客户端密钥")]
    name: Annotated[str, Field(..., description="应用名称")]
    logo: Annotated[str, Field(..., description="应用图标")]
    description: Annotated[str | None, Field(None, description="应用描述")]
    status: Annotated[int, Field(..., description="状态,参见 StatusEnum 枚举")]
    user_type: Annotated[int | None, Field(None, description="绑定的用户类型")]
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
    additional_information: Annotated[str | None, Field(None, description="附加信息")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "clientId": "lele",
                    "secret": "fan",
                    "name": "乐乐",
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
                    "additionalInformation": "{lele: true}",
                }
            ]
        }
    }

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="client_id", value=v, error_msg="客户端编号不能为空")
        return v

    @field_validator("secret", mode="before")
    @classmethod
    def _validate_secret(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="secret", value=v, error_msg="客户端密钥不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="应用名不能为空")
        return v

    @field_validator("logo", mode="before")
    @classmethod
    def _validate_logo(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="logo", value=v, error_msg="应用图标不能为空")
        URL.require_url(field_name="logo", value=v, error_msg="应用图标的地址无法识别")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="状态必须在指定范围"
        )
        return v

    @field_validator("access_token_validity_seconds", mode="before")
    @classmethod
    def _validate_access_token_validity_seconds(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="access_token_validity_seconds",
            value=v,
            error_msg="访问令牌的有效期不能为空",
        )
        return v

    @field_validator("refresh_token_validity_seconds", mode="before")
    @classmethod
    def _validate_refresh_token_validity_seconds(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="refresh_token_validity_seconds",
            value=v,
            error_msg="刷新令牌的有效期不能为空",
        )
        return v

    @field_validator("redirect_uris", mode="before")
    @classmethod
    def _validate_redirect_uris(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="redirect_uris", value=v, error_msg="可重定向的 URI 地址不能为空"
        )
        return v

    @field_validator("authorized_grant_types", mode="before")
    @classmethod
    def _validate_authorized_grant_types(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="authorized_grant_types", value=v, error_msg="授权类型不能为空"
        )
        if not isinstance(v, list):
            raise ValueError("授权类型必须是一个列表")
        if v:
            allowed_values_str = str(
                OAuth2GrantTypeEnum.get_codes()
                if hasattr(OAuth2GrantTypeEnum, "get_codes")
                else [m.value for m in OAuth2GrantTypeEnum]
            )
            for grant_type in v:
                try:
                    InEnum.require_in_enum(
                        field_name=f"授权类型 '{grant_type}'",
                        value=grant_type,
                        enum_class=OAuth2GrantTypeEnum,
                        error_msg=f"授权类型 '{grant_type}' 必须在指定范围 {allowed_values_str}",
                    )
                except ValueError as e:
                    raise ValueError(str(e))
                except Exception as e:
                    raise ValueError(f"验证授权类型 '{grant_type}' 时发生意外错误: {e}")
        return v
