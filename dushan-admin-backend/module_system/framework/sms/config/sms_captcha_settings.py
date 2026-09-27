from typing import Annotated

from pydantic import Field, model_validator

from framework.starter_config.public import (
    ConfigModel,
    ConfigSourceEnum,
    config_model,
)
from module_system.definitions.constants.sms_code_constants import SmsCodeConstants


@config_model(
    "sms_captcha",
    env_prefix="SMS_CAPTCHA_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class SmsCaptchaSettings(ConfigModel):
    debug_enabled: bool
    debug_mobiles: tuple[Annotated[str, Field(strict=True, pattern=r"^1[3-9]\d{9}$")], ...]
    expire_times: int = Field(gt=0)
    max_attempts: int = Field(ge=1, le=10)
    send_frequency: int = Field(gt=0)
    send_maximum_quantity_per_day: int = Field(gt=0)
    begin_code: int = Field(ge=1000, le=999999)
    end_code: int = Field(ge=1000, le=999999)

    @model_validator(mode="after")
    def validate_range(self):
        if self.begin_code > self.end_code:
            raise ValueError("验证码起始值不能大于结束值")
        if self.begin_code == self.end_code == int(SmsCodeConstants.DEBUG_CODE):
            raise ValueError("8888 是调试保留码，正常验证码范围必须包含其他值")
        return self
