from pydantic import Field, model_validator

from framework.starter_auth.config.auth_client_config import AuthClientConfig
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model


@config_model("auth", env_prefix="AUTH_")
class AuthSettings(ConfigModel):
    """应用资源配置；默认值只由公共 YAML 提供，修改后重启生效。"""

    enabled: bool
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    client_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    state_ttl_seconds: int = Field(strict=True, ge=1, le=600)
    operation_timeout_seconds: float = Field(gt=0, le=120, allow_inf_nan=False)
    http_timeout_seconds: float = Field(gt=0, le=60, allow_inf_nan=False)
    max_connections: int = Field(strict=True, ge=1, le=256)
    max_response_bytes: int = Field(strict=True, ge=1024, le=4_194_304)
    allow_loopback_http: bool
    proxy: str | None = Field(repr=False)
    jwks_ttl_seconds: int = Field(strict=True, ge=1, le=86400)
    jwks_refresh_cooldown_seconds: float = Field(gt=0, le=300, allow_inf_nan=False)
    jwks_max_keys: int = Field(strict=True, ge=1, le=64)
    oidc_leeway_seconds: int = Field(strict=True, ge=0, le=120)
    credential_ttl_seconds: int = Field(strict=True, ge=1, le=86400)
    credential_expiry_margin_seconds: int = Field(strict=True, ge=1, le=600)
    tracing_enabled: bool
    clients: tuple[AuthClientConfig, ...]

    @model_validator(mode="after")
    def validate_clients(self) -> "AuthSettings":
        keys = [(c.application_id, c.source) for c in self.clients]
        if len(keys) != len(set(keys)):
            raise ValueError("授权客户端的 application_id/source 不能重复")
        return self

    def cache_keys(self) -> tuple[CacheKey, CacheKey]:
        return tuple(
            CacheKey(key=f"auth:{kind}", remark=remark, client_name=self.client_name)
            for kind, remark in (
                ("state", "第三方授权一次性上下文"),
                ("credential", "第三方应用凭据"),
            )
        )
