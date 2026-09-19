import re

from pydantic import Field, model_validator

from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum


@config_model(
    "security",
    env_prefix="SECURITY_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class SecuritySettings(ConfigModel):
    """部署默认值只来自公共 YAML；认证域和应用编号参与所有身份绑定。"""

    enabled: bool
    application_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    domains: tuple[str, ...]
    default_domain: str
    permission_cache_enabled: bool
    permission_cache_client: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    permission_cache_ttl_seconds: int = Field(strict=True, ge=1, le=300)
    provider_timeout_seconds: float = Field(gt=0, le=60, allow_inf_nan=False)
    bcrypt_rounds: int = Field(strict=True, ge=12, le=16)
    password_concurrency: int = Field(strict=True, ge=1, le=32)
    bizlog_enabled: bool
    bizlog_renew_seconds: float = Field(gt=0, le=300, allow_inf_nan=False)
    bizlog_max_length: int = Field(strict=True, ge=128, le=4096)
    bizlog_max_diff_items: int = Field(strict=True, ge=1, le=100)

    @model_validator(mode="after")
    def validate_domains(self):
        if not self.domains or len(set(self.domains)) != len(self.domains):
            raise ValueError("认证域不能为空或重复")
        if any(re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value) is None for value in self.domains):
            raise ValueError("认证域必须使用明确的标识符")
        if self.default_domain not in self.domains:
            raise ValueError("默认认证域必须包含在 domains 中")
        if self.bizlog_enabled and not self.enabled:
            raise ValueError("业务审计要求启用 Security")
        return self

    def cache_key(self) -> CacheKey:
        return CacheKey(
            key="security:permissions",
            remark="绑定实时授权版本的权限快照",
            client_name=self.permission_cache_client,
        )
