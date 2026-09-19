from pydantic import Field, SecretStr

from framework.starter_config.public import (
    ConfigModel,
    ConfigSourceEnum,
    config_model,
)


@config_model(
    "system", env_prefix="SYSTEM_", sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML)
)
class SystemSettings(ConfigModel):
    user_register_enabled: bool
    allow_modify_system_role: bool
    default_client_id: str = Field(min_length=1)
    default_password: SecretStr | None
    code_expire_seconds: int = Field(gt=0)
    approve_expire_seconds: int = Field(gt=0)
    refresh_cookie_name: str = Field(min_length=1)
    refresh_cookie_secure: bool
    allowed_origins: tuple[str, ...]
    workload_credential: SecretStr | None
    message_signing_key: SecretStr | None
    sms_callback_token: SecretStr | None
    message_lifetime_seconds: int = Field(ge=1, le=3600)
