from pydantic import Field

from framework.starter_config.public import ConfigModel, ConfigSourceEnum, config_model


@config_model(
    "qr_login",
    env_prefix="QR_LOGIN_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class QrLoginSettings(ConfigModel):
    enabled: bool
    expire_seconds: int = Field(ge=60, le=600)
