from pydantic import Field

from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum


@config_model(
    "data_permission",
    env_prefix="DATA_PERMISSION_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class DataPermissionSettings(ConfigModel):
    enabled: bool
    snapshot_seconds: float = Field(gt=0, le=300, allow_inf_nan=False)
    provider_timeout_seconds: float = Field(gt=0, le=60, allow_inf_nan=False)
    in_clause_chunk_size: int = Field(strict=True, ge=1, le=1000)
    cache_enabled: bool
    cache_client: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    cache_ttl_seconds: int = Field(strict=True, ge=1, le=300)
    rule_version: str = Field(min_length=1, max_length=64)

    def cache_key(self) -> CacheKey:
        return CacheKey(
            key="data_permission:scope",
            remark="按完整身份、授权和规则版本绑定的数据范围",
            client_name=self.cache_client,
        )
