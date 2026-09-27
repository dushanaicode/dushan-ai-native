from pydantic import Field

from framework.starter_config.public import ConfigModel, ConfigSourceEnum, config_model


@config_model(
    "password_reset",
    env_prefix="PASSWORD_RESET_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class PasswordResetSettings(ConfigModel):
    mail_template_code: str = Field(min_length=1)
    expire_seconds: int = Field(ge=60, le=3600)
    resend_seconds: int = Field(ge=1, le=3600)
    max_attempts: int = Field(ge=1, le=10)
    max_daily: int = Field(ge=1, le=100)
