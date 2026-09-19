from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.validator import NotEmpty, NotNull, Pattern, Size
from module_system.controller.admin.auth.vo.auth_captcha_verification_req_vo import (
    CaptchaVerificationReqVO,
)


class AuthRegisterReqVO(CaptchaVerificationReqVO):
    """管理后台 - 注册 Request VO"""

    username: Annotated[str, Field(..., description="用户账号")]
    nickname: Annotated[str, Field(..., description="用户昵称")]
    password: Annotated[str, Field(..., description="密码")]
    client_id: str | None = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "lele",
                    "nickname": "乐乐",
                    "password": "123456",
                    "captchaVerification": "PfcH6mgr8tpXuMWFjvW6YVaqrswIuwmWI5dsVZSg7sGpWtDCUbHuDEXl3cFB1+VvCC/rAkSwK8Fad52FSuncVg==",
                }
            ]
        }
    }

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="username", value=v, error_msg="用户账号不能为空")
        Pattern.require_pattern(
            field_name="username",
            value=v,
            pattern="^[a-zA-Z0-9]{4,30}$",
            error_msg="用户账号由数字、字母组成",
        )
        Size.require_size(
            field_name="username",
            value=v,
            min_length=4,
            max_length=30,
            error_msg="用户账号长度为4-30个字符",
        )
        return v

    @field_validator("nickname", mode="before")
    @classmethod
    def _validate_nickname(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="nickname", value=v, error_msg="用户昵称不能为空")
        Size.require_size(
            field_name="nickname",
            value=v,
            min_length=0,
            max_length=30,
            error_msg="用户昵称长度不能超过30个字符",
        )
        return v

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

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> Any:
        if v is None:
            return v
        NotEmpty.require_not_empty(field_name="client_id", value=v, error_msg="客户端ID不能为空")
        return v
