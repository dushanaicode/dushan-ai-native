from pydantic import Field, model_validator

from framework.starter_config.public import (
    ConfigModel,
    ConfigSourceEnum,
    config_model,
)


@config_model(
    "sms_captcha",
    env_prefix="SMS_CAPTCHA_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class SmsCaptchaSettings(ConfigModel):
    expire_times: int = Field(gt=0)
    send_frequency: int = Field(gt=0)
    send_maximum_quantity_per_day: int = Field(gt=0)
    begin_code: int = Field(ge=1000, le=999999)
    end_code: int = Field(ge=1000, le=999999)

    @model_validator(mode="after")
    def validate_range(self):
        if self.begin_code > self.end_code:
            raise ValueError("验证码起始值不能大于结束值")
        return self
