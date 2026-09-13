import re
from typing import Literal

from pydantic import Field, model_validator

from framework.starter_captcha.config.aliyun_captcha_settings import AliyunCaptchaSettings
from framework.starter_captcha.config.tencent_captcha_settings import TencentCaptchaSettings
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model


@config_model("captcha", env_prefix="CAPTCHA_")
class CaptchaSettings(ConfigModel):
    """验证码启动快照；默认值由 application.yaml 提供，变更后重启生效。"""

    enabled: bool
    provider: Literal["block_puzzle", "click_word", "aliyun", "tencent"]
    purposes: tuple[str, ...]
    client_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    challenge_ttl_seconds: int = Field(strict=True, ge=1, le=600)
    verification_ttl_seconds: int = Field(strict=True, ge=1, le=300)
    max_attempts: int = Field(strict=True, ge=1, le=10)
    slider_tolerance: float = Field(strict=True, ge=0, le=10, allow_inf_nan=False)
    click_tolerance: float = Field(strict=True, ge=0, le=20, allow_inf_nan=False)
    generation_concurrency: int = Field(strict=True, ge=1, le=16)
    generation_limit: int = Field(strict=True, ge=1, le=10000)
    generation_window_seconds: int = Field(strict=True, ge=1, le=600)
    interference: int = Field(strict=True, ge=0, le=2)
    background_dir: str | None
    watermark: str = Field(max_length=16)
    tracing_enabled: bool
    cloud_timeout_seconds: float = Field(strict=True, gt=0, le=30, allow_inf_nan=False)
    cloud_max_connections: int = Field(strict=True, ge=1, le=100)
    cloud_max_response_bytes: int = Field(strict=True, ge=1024, le=262144)
    aliyun: AliyunCaptchaSettings
    tencent: TencentCaptchaSettings

    @model_validator(mode="after")
    def validate_selection(self) -> "CaptchaSettings":
        """用途由服务端声明，未选中的云配置允许为空。"""
        if not self.purposes or len(set(self.purposes)) != len(self.purposes):
            raise ValueError("验证码用途不能为空或重复")
        if any(re.fullmatch(r"[a-z][a-z0-9_]{0,63}", p) is None for p in self.purposes):
            raise ValueError("验证码用途格式无效")
        if self.enabled and self.provider in ("aliyun", "tencent"):
            getattr(self, self.provider).require_credentials()
        return self
