from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.size import Size


class UserProfileUpdatePasswordReqVO(BaseRequestVO):
    """管理后台 - 用户个人中心更新密码 Request VO"""

    old_password: Annotated[str, Field(..., description="旧密码")]
    new_password: Annotated[str, Field(..., description="新密码")]
    model_config = {
        "json_schema_extra": {"examples": [{"oldPassword": "123456", "newPassword": "654321"}]}
    }

    @field_validator("old_password", mode="before")
    @classmethod
    def _validate_old_password_not_empty_size(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="old_password", value=v, error_msg="旧密码不能为空")
        Size.require_size(
            field_name="old_password",
            value=v,
            min_length=4,
            max_length=16,
            error_msg="密码长度为 4-16 位",
        )
        return v

    @field_validator("new_password", mode="before")
    @classmethod
    def _validate_new_password_not_empty_size(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="new_password", value=v, error_msg="新密码不能为空")
        Size.require_size(
            field_name="new_password",
            value=v,
            min_length=4,
            max_length=16,
            error_msg="密码长度为 4-16 位",
        )
        return v
