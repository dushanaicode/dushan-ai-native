from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.email import Email
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull


class MailTemplateSendReqVO(BaseRequestVO):
    """管理后台 - 邮件发送 Request VO"""

    to_mails: Annotated[list[str], Field(..., description="接收邮箱列表")]
    cc_mails: Annotated[list[str] | None, Field(None, description="抄送邮箱列表")]
    bcc_mails: Annotated[list[str] | None, Field(None, description="密送邮箱列表")]
    template_code: Annotated[str, Field(..., description="模板编码")]
    template_params: Annotated[dict[str, Any], Field(default_factory=dict, description="模板参数")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "toMails": ["user1@example.com", "user2@example.com"],
                    "ccMails": ["user3@example.com", "user4@example.com"],
                    "bccMails": ["user5@example.com", "user6@example.com"],
                    "templateCode": "test_01",
                    "templateParams": {"key": "value"},
                }
            ]
        }
    }

    @field_validator("to_mails", mode="before")
    @classmethod
    def _validate_to_mails(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="to_mails", value=v, error_msg="接收邮箱列表不能为空")
        if isinstance(v, list):
            for mail in v:
                Email.require_email(field_name="to_mails", value=mail, error_msg="邮箱格式错误")
        return v

    @field_validator("cc_mails", mode="before")
    @classmethod
    def _validate_cc_mails(cls, v: Any) -> Any:
        if isinstance(v, list):
            for mail in v:
                Email.require_email(field_name="cc_mails", value=mail, error_msg="抄送邮箱格式错误")
        return v

    @field_validator("bcc_mails", mode="before")
    @classmethod
    def _validate_bcc_mails(cls, v: Any) -> Any:
        if isinstance(v, list):
            for mail in v:
                Email.require_email(
                    field_name="bcc_mails", value=mail, error_msg="密送邮箱格式错误"
                )
        return v

    @field_validator("template_code", mode="before")
    @classmethod
    def _validate_template_code(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="template_code", value=v, error_msg="模板编码不能为空")
        return v
