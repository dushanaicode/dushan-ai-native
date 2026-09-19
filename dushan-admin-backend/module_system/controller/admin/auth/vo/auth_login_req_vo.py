from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.validator import AssertTrue, InEnum, Length, NotEmpty, Pattern
from module_system.controller.admin.auth.vo.auth_captcha_verification_req_vo import (
    CaptchaVerificationReqVO,
)
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum


class AuthLoginReqVO(CaptchaVerificationReqVO):
    """管理后台 - 账号密码登录 Request VO，如果登录并绑定社交用户，需要传递 social 开头的参数"""

    username: Annotated[str, Field(..., description="账号")]
    password: Annotated[str, Field(..., description="密码")]
    social_type: Annotated[
        int | None, Field(None, description="社交平台的类型，参见 SocialTypeEnum 枚举值")
    ]
    social_code: Annotated[str | None, Field(None, description="授权码")]
    social_state: Annotated[str | None, Field(None, description="state")]
    client_id: str | None = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "dushan",
                    "password": "123456",
                    "socialType": 10,
                    "socialCode": "1024",
                    "socialState": "9b2ffbc1-7425-4155-9894-9d5c08541d62",
                    "captchaVerification": "PfcH6mgr8tpXuMWFjvW6YVaqrswIuwmWI5dsVZSg7sGpWtDCUbHuDEXl3cFB1+VvCC/rAkSwK8Fad52FSuncVg==",
                }
            ]
        }
    }

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="username", value=v, error_msg="登录账号不能为空")
        Length.require_length(
            field_name="username",
            value=v,
            min_length=4,
            max_length=16,
            error_msg="账号长度为 4-16 位",
        )
        Pattern.require_pattern(
            field_name="username",
            value=v,
            pattern="^[A-Za-z0-9]+$",
            error_msg="账号格式为数字以及字母",
        )
        return v

    @field_validator("password", mode="before")
    @classmethod
    def _validate_password(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="password", value=v, error_msg="密码不能为空")
        Length.require_length(
            field_name="password",
            value=v,
            min_length=4,
            max_length=16,
            error_msg="密码长度为 4-16 位",
        )
        return v

    @field_validator("social_type", mode="before")
    @classmethod
    def _validate_social_type(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(
                field_name="social_type",
                value=v,
                enum_class=SocialTypeEnum,
                error_msg="社交平台类型不正确",
            )
        return v

    @field_validator("social_code", mode="before")
    @classmethod
    def _validate_social_code(cls, v: Any) -> Any:
        if v is not None:
            AssertTrue.require_true(
                field_name="social_code", value=bool(v), error_msg="授权码不能为空"
            )
        return v

    @field_validator("social_state", mode="before")
    @classmethod
    def _validate_social_state(cls, v: Any) -> Any:
        if v is not None:
            AssertTrue.require_true(
                field_name="social_state", value=bool(v), error_msg="授权 state 不能为空"
            )
        return v

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> Any:
        if v is None:
            return v
        NotEmpty.require_not_empty(field_name="client_id", value=v, error_msg="客户端ID不能为空")
        return v
