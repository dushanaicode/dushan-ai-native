import hashlib
import json

from pydantic import Field, SecretStr, field_validator, model_validator

from framework.starter_auth.model.provider_capability import AUTH_SOURCE_PATTERN
from framework.starter_config.config.config_model import ConfigModel


class AuthClientConfig(ConfigModel):
    """业务应用的授权客户端快照；配置 SPI 必须返回请求所指定的同一身份。"""

    application_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    source: str = Field(pattern=AUTH_SOURCE_PATTERN)
    enabled: bool
    revision: int = Field(strict=True, ge=1)
    client_id: str | None = Field(min_length=1, max_length=256)
    client_secret: SecretStr | None = Field(exclude=True, repr=False)
    redirect_uri: str | None
    scopes: tuple[str, ...]
    pkce: bool
    options: dict[str, str]
    credentials: dict[str, SecretStr] = Field(exclude=True, repr=False)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) > 64 or len(set(values)) != len(values):
            raise ValueError("授权 scope 过多或重复")
        if any(not v or len(v) > 256 or any(c.isspace() for c in v) for v in values):
            raise ValueError("授权 scope 格式无效")
        return values

    @model_validator(mode="after")
    def validate_credentials(self) -> "AuthClientConfig":
        if self.enabled and (
            self.client_id is None
            or self.client_secret is None
            or not self.client_secret.get_secret_value()
        ):
            raise ValueError("启用的授权客户端必须提供 client_id 和 client_secret")
        return self

    def fingerprint(self) -> str:
        """绑定全部有效配置，凭据变更而忘记递增 revision 时也拒绝旧流程。"""
        values = self.model_dump(mode="json")
        values["client_secret"] = (
            None if self.client_secret is None else self.client_secret.get_secret_value()
        )
        values["credentials"] = {k: v.get_secret_value() for k, v in self.credentials.items()}
        return hashlib.sha256(
            json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
