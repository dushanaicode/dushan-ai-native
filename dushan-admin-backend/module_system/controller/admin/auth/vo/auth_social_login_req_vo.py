from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum


class AuthSocialLoginReqVO(BaseRequestVO):
    """管理后台 - 社交绑定登录 Request VO"""

    type: Annotated[int, Field(..., description="社交平台的类型，参见 SocialTypeEnum 枚举值")]
    code: Annotated[str, Field(..., description="授权码")]
    state: Annotated[str, Field(..., description="state")]
    client_id: str | None = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"type": 10, "code": "1024", "state": "9b2ffbc1-7425-4155-9894-9d5c08541d62"}
            ]
        }
    }

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="type", value=v, error_msg="社交平台的类型不能为空")
        InEnum.require_in_enum(
            field_name="type",
            value=v,
            enum_class=SocialTypeEnum,
            error_msg="社交平台的类型必须在指定范围 {values}",
        )
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="code", value=v, error_msg="授权码不能为空")
        return v

    @field_validator("state", mode="before")
    @classmethod
    def _validate_state(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="state", value=v, error_msg="state 不能为空")
        return v

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> Any:
        if v is None:
            return v
        NotEmpty.require_not_empty(field_name="client_id", value=v, error_msg="客户端ID不能为空")
        return v
