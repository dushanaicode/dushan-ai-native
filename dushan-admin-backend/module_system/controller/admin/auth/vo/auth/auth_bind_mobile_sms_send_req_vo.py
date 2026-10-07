from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas import BaseRequestVO
from framework.common.validator import Mobile, NotEmpty


class AuthBindMobileSmsSendReqVO(BaseRequestVO):
    """管理后台 - 已登录用户发送绑定手机验证码 Request VO"""

    mobile: Annotated[str, Field(..., description="手机号")]
    model_config = {"json_schema_extra": {"examples": [{"mobile": "13312341234"}]}}

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="mobile", value=v, error_msg="手机号不能为空")
        Mobile.require_mobile(field_name="mobile", value=v, error_msg="手机号格式不正确")
        return v
