from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.validator import NotEmpty, Size
from module_system.controller.admin.auth.vo.auth.auth_recovery_contact_req_vo import (
    AuthRecoveryContactReqVO,
)


class AuthResetPasswordReqVO(AuthRecoveryContactReqVO):
    """管理后台 - 通过已绑定的手机号或邮箱重置密码。"""

    password: Annotated[str, Field(..., description="密码")]
    code: Annotated[str, Field(..., description="收到的验证码", pattern=r"^\d{4,6}$")]
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

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="code", value=v, error_msg="验证码不能为空")
        return v
