from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.not_null import NotNull


class OAuth2OpenAccessTokenRespVO(BaseVO):
    """管理后台 - 【开放接口】访问令牌 Response VO"""

    access_token: Annotated[str, Field(..., description="访问令牌")]
    refresh_token: Annotated[str, Field(..., description="刷新令牌")]
    token_type: Annotated[str, Field(..., description="令牌类型")]
    expires_in: Annotated[int, Field(..., description="过期时间,单位：秒")]
    scope: Annotated[str | None, Field(None, description="授权范围,如果多个授权范围，使用空格分隔")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "accessToken": "dushan",
                    "refreshToken": "nice",
                    "tokenType": "bearer",
                    "expiresIn": 42430,
                    "scope": "user_info",
                }
            ]
        }
    }

    @field_validator("access_token", mode="before")
    @classmethod
    def _validate_access_token(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="access_token", value=v, error_msg="访问令牌不能为空")
        return v

    @field_validator("refresh_token", mode="before")
    @classmethod
    def _validate_refresh_token(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="refresh_token", value=v, error_msg="刷新令牌不能为空")
        return v

    @field_validator("token_type", mode="before")
    @classmethod
    def _validate_token_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="token_type", value=v, error_msg="令牌类型不能为空")
        return v

    @field_validator("expires_in", mode="before")
    @classmethod
    def _validate_expires_in(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="expires_in", value=v, error_msg="过期时间不能为空")
        return v
