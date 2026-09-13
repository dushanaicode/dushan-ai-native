from pydantic import Field, SecretStr

from framework.starter_config.config.config_model import ConfigModel


class TencentCaptchaSettings(ConfigModel):
    app_id: int = Field(strict=True, ge=0, le=2**63 - 1)
    app_secret: SecretStr
    secret_id: SecretStr
    secret_key: SecretStr

    def require_credentials(self) -> None:
        if not self.app_id or not all(
            (
                self.app_secret.get_secret_value(),
                self.secret_id.get_secret_value(),
                self.secret_key.get_secret_value(),
            )
        ):
            raise ValueError("启用腾讯验证码要求完整的应用与 API 凭据")
