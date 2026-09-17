from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.validator.mobile import Mobile
from framework.common.validator.not_empty import NotEmpty
from module_system.controller.admin.auth.vo.auth_captcha_verification_req_vo import (
    CaptchaVerificationReqVO,
)


class AuthSmsLoginReqVO(CaptchaVerificationReqVO):
    """管理后台 - 短信验证码登录 Request VO"""

    mobile: Annotated[str, Field(..., description="手机号")]
    code: Annotated[str, Field(..., description="短信验证码")]
    client_id: str | None = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "mobile": "13312341234",
                    "code": "123456",
                    "captchaVerification": "PfcH6mgr8tpXuMWFjvW6YVaqrswIuwmWI5dsVZSg7sGpWtDCUbHuDEXl3cFB1+VvCC/rAkSwK8Fad52FSuncVg==",
                }
            ]
        }
    }

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

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> Any:
        if v is None:
            return v
        NotEmpty.require_not_empty(field_name="client_id", value=v, error_msg="客户端ID不能为空")
        return v
