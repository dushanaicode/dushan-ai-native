from typing import Any

from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_empty import NotEmpty


class CaptchaVerificationReqVO(BaseRequestVO):
    """管理后台 - 验证码 Request VO"""

    verification: str | None = Field(None, description="验证码，验证码开启时，需要传递")
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "captchaVerification": "PfcH6mgr8tpXuMWFjvW6YVaqrswIuwmWI5dsVZSg7sGpWtDCUbHuDEXl3cFB1+VvCC/rAkSwK8Fad52FSuncVg=="
                }
            ]
        }
    }

    @field_validator("verification", mode="before")
    @classmethod
    def _validate_verification(cls, v: Any) -> Any:
        if v is not None:
            NotEmpty.require_not_empty(
                field_name="verification", value=v, error_msg="验证码不能为空"
            )
        return v
