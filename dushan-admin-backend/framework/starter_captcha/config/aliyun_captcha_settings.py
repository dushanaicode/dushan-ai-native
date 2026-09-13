from typing import Literal

from pydantic import SecretStr, model_validator

from framework.starter_config.config.config_model import ConfigModel


class AliyunCaptchaSettings(ConfigModel):
    access_key_id: SecretStr
    access_key_secret: SecretStr
    scene_id: str
    prefix: str
    region: Literal["cn", "sgp"]
    language: Literal["cn", "en"]
    endpoint: str

    @model_validator(mode="after")
    def validate_endpoint(self) -> "AliyunCaptchaSettings":
        region = "cn-shanghai" if self.region == "cn" else "ap-southeast-1"
        if self.endpoint not in {
            f"{p}.{region}.aliyuncs.com" for p in ("captcha", "captcha-dualstack", "captcha-vpc")
        }:
            raise ValueError("阿里云验证码 endpoint 与 region 不匹配")
        return self

    def require_credentials(self) -> None:
        if not all(
            (
                self.access_key_id.get_secret_value(),
                self.access_key_secret.get_secret_value(),
                self.scene_id.strip(),
                self.prefix.strip(),
            )
        ):
            raise ValueError("启用阿里云验证码要求完整的凭据、scene_id 和 prefix")
