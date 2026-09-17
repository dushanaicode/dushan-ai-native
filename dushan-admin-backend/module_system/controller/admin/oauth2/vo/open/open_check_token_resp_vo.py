from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.not_null import NotNull


class OAuth2OpenCheckTokenRespVO(BaseVO):
    """管理后台 - 【开放接口】校验令牌 Response VO"""

    user_id: Annotated[SnowflakeIdStr, Field(..., description="用户编号")]
    user_type: Annotated[int, Field(..., description="用户类型，参见 UserTypeEnum 枚举")]
    tenant_id: Annotated[str, Field(..., description="租户编号")]
    client_id: Annotated[str, Field(..., description="客户端编号")]
    scopes: Annotated[list[str], Field(..., description="授权范围")]
    access_token: Annotated[str, Field(..., description="访问令牌")]
    exp: Annotated[int, Field(..., description="过期时间，时间戳 / 1000，即单位：秒")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userId": 666,
                    "userType": 2,
                    "tenantId": 1024,
                    "clientId": "car",
                    "scopes": ["user_info"],
                    "accessToken": "dushan",
                    "exp": 1593092157,
                }
            ]
        }
    }

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="user_id", value=v, error_msg="用户编号不能为空")
        return v

    @field_validator("user_type", mode="before")
    @classmethod
    def _validate_user_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="user_type", value=v, error_msg="用户类型不能为空")
        return v

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _validate_tenant_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="tenant_id", value=v, error_msg="租户编号不能为空")
        return v

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="client_id", value=v, error_msg="客户端编号不能为空")
        return v

    @field_validator("scopes", mode="before")
    @classmethod
    def _validate_scopes(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="scopes", value=v, error_msg="授权范围不能为空")
        return v

    @field_validator("access_token", mode="before")
    @classmethod
    def _validate_access_token(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="access_token", value=v, error_msg="访问令牌不能为空")
        return v

    @field_validator("exp", mode="before")
    @classmethod
    def _validate_exp(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="exp", value=v, error_msg="过期时间不能为空")
        return v
