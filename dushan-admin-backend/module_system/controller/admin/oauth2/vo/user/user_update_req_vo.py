from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.email import Email
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.size import Size


class OAuth2UserUpdateReqVO(BaseRequestVO):
    """管理后台 - OAuth2 更新用户基本信息 Request VO"""

    nickname: Annotated[str, Field(..., description="用户昵称")]
    email: Annotated[str | None, Field(None, description="用户邮箱")]
    mobile: Annotated[str | None, Field(None, description="手机号码")]
    sex: Annotated[int | None, Field(None, description="用户性别，参见 CommonSexEnum 枚举类")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"nickname": "渡山", "email": "729227973@qq.com", "mobile": "18888888888", "sex": 1}
            ]
        }
    }

    @field_validator("nickname", mode="before")
    @classmethod
    def _validate_nickname(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="nickname", value=v, error_msg="用户昵称不能为空")
        Size.require_size(
            field_name="nickname",
            value=v,
            min_length=0,
            max_length=30,
            error_msg="用户昵称长度不能超过 30 个字符",
        )
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _validate_email(cls, v: Any) -> Any:
        if v:
            Email.require_email(field_name="email", value=v, error_msg="邮箱格式不正确")
            Size.require_size(
                field_name="email",
                value=v,
                min_length=0,
                max_length=50,
                error_msg="邮箱长度不能超过 50 个字符",
            )
        return v

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile(cls, v: Any) -> Any:
        if v:
            Size.require_size(
                field_name="mobile",
                value=v,
                min_length=11,
                max_length=11,
                error_msg="手机号长度必须 11 位",
            )
        return v
