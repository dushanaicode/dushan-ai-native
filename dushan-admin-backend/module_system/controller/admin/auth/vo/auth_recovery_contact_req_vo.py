from typing import Literal

from pydantic import model_validator

from framework.common.schemas import BaseRequestVO
from framework.common.validator import Email, Mobile


class AuthRecoveryContactReqVO(BaseRequestVO):
    channel: Literal["sms", "email"] = "sms"
    mobile: str | None = None
    email: str | None = None

    @model_validator(mode="after")
    def validate_contact(self):
        if self.channel == "sms":
            if self.mobile is None or self.email is not None:
                raise ValueError("短信找回仅填写手机号")
            Mobile.require_mobile(field_name="mobile", value=self.mobile)
        else:
            if self.email is None or self.mobile is not None:
                raise ValueError("邮箱找回仅填写邮箱地址")
            Email.require_email(field_name="email", value=self.email)
        return self
