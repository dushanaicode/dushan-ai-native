from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.mobile import Mobile
from framework.common.validator.not_empty import NotEmpty


class AuthBindMobileReqVO(BaseRequestVO):
    """管理后台 - 绑定手机号 Request VO"""

    mobile: Annotated[str, Field(..., description="手机号")]
    code: Annotated[str, Field(..., description="手机短信验证码")]
    model_config = {
        "json_schema_extra": {"examples": [{"mobile": "13312341234", "code": "123456"}]}
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
