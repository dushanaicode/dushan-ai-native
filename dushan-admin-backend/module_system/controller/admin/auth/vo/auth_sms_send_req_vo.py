from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.validator import InEnum, Mobile, NotEmpty, NotNull
from module_system.controller.admin.auth.vo.auth_captcha_verification_req_vo import (
    CaptchaVerificationReqVO,
)
from module_system.definitions.enums.sms.sms_scene_enum import SmsSceneEnum


class AuthSmsSendReqVO(CaptchaVerificationReqVO):
    """管理后台 - 发送手机验证码 Request VO"""

    mobile: Annotated[str, Field(..., description="手机号")]
    scene: Annotated[int, Field(..., description="短信场景")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "mobile": "13312341234",
                    "scene": 1,
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

    @field_validator("scene", mode="before")
    @classmethod
    def _validate_scene(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="scene", value=v, error_msg="发送场景不能为空")
        InEnum.require_in_enum(
            field_name="scene",
            value=v,
            enum_class=SmsSceneEnum,
            error_msg="短信场景必须在指定范围 {values}",
        )
        return v
