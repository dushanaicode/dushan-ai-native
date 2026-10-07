from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas import BaseRequestVO
from framework.common.validator import InEnum, NotEmpty, NotNull
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum


class SocialUserUnbindReqVO(BaseRequestVO):
    """管理后台 - 取消社交绑定 Request VO"""

    type: Annotated[int, Field(..., description="社交平台的类型，参见 SocialTypeEnum 枚举值")]
    openid: Annotated[str, Field(..., description="社交用户的 openid")]
    model_config = {
        "json_schema_extra": {"examples": [{"type": 10, "openid": "IPRmJ0wvBptiPIlGEZiPewGwiEiE"}]}
    }

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type_enum(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="type", value=v, error_msg="社交平台的类型不能为空")
        InEnum.require_in_enum(
            field_name="type",
            value=v,
            enum_class=SocialTypeEnum,
            error_msg="社交平台的类型必须在指定范围内",
        )
        return v

    @field_validator("openid", mode="before")
    @classmethod
    def _validate_openid_not_empty(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(
            field_name="openid", value=v, error_msg="社交用户的 openid 不能为空"
        )
        return v
