from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas import BaseRequestVO
from framework.common.validator import Mobile, NotEmpty, Size


class AuthResetPasswordReqVO(BaseRequestVO):
    """管理后台 - 短信重置账号密码 Request VO"""

    password: Annotated[str, Field(..., description="密码")]
    mobile: Annotated[str, Field(..., description="手机号")]
    code: Annotated[str, Field(..., description="手机短信验证码")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"password": "1234", "mobile": "13312341234", "code": "123456"}]
        }
    }

    @field_validator("password", mode="before")
    @classmethod
    def _validate_password(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="password", value=v, error_msg="密码不能为空")
        Size.require_size(
            field_name="password",
            value=v,
            min_length=4,
            max_length=16,
            error_msg="密码长度为4-16位",
        )
        return v

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="mobile", value=v, error_msg="手机号不能为空")
        Mobile.require_mobile(field_name="mobile", value=v, error_msg="手机号格式不正确")
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="code", value=v, error_msg="手机短信验证码不能为空")
        return v
