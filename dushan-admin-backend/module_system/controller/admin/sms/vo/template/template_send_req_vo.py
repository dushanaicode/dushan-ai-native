from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_null import NotNull


class SmsTemplateSendReqVO(BaseRequestVO):
    """管理后台 - 短信模板发送 Request VO"""

    mobile: Annotated[str, Field(..., description="手机号")]
    template_code: Annotated[str, Field(..., description="模板编码")]
    template_params: Annotated[dict[str, Any], Field(default_factory=dict, description="模板参数")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "mobile": "18888888888",
                    "templateCode": "test_01",
                    "templateParams": {"name": "张三", "code": "1234"},
                }
            ]
        }
    }

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile(cls, value: str) -> str:
        NotNull.require_not_null(field_name="mobile", value=value, error_msg="手机号不能为空")
        return value

    @field_validator("template_code", mode="before")
    @classmethod
    def _validate_template_code(cls, value: str) -> str:
        NotNull.require_not_null(
            field_name="template_code", value=value, error_msg="模板编码不能为空"
        )
        return value
