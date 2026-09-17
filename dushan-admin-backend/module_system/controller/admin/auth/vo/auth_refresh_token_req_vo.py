from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_empty import NotEmpty


class AuthRefreshTokenReqVO(BaseRequestVO):
    """管理后台 - 刷新令牌 Request VO"""

    refresh_token: Annotated[str, Field(..., description="刷新令牌")]
    client_id: str | None = None

    @field_validator("refresh_token", mode="before")
    @classmethod
    def _validate_refresh_token(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(
            field_name="refresh_token", value=v, error_msg="刷新令牌不能为空"
        )
        return v

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> Any:
        if v is None:
            return v
        NotEmpty.require_not_empty(field_name="client_id", value=v, error_msg="客户端ID不能为空")
        return v
