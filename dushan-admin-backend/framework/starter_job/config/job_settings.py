from pydantic import Field, model_validator

from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.enums.config_source_enum import ConfigSourceEnum


@config_model(
    "job", env_prefix="JOB_", sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML)
)
class JobSettings(ConfigModel):
    enabled: bool
    owner_enabled: bool
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    cache_client: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    timezone: str | None
    reconciliation_seconds: float = Field(gt=0, allow_inf_nan=False)
    poll_seconds: float = Field(gt=0, allow_inf_nan=False)
    owner_lease_seconds: float = Field(gt=0, allow_inf_nan=False)
    owner_renew_seconds: float = Field(gt=0, allow_inf_nan=False)
    command_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    misfire_grace_seconds: int = Field(strict=True, ge=1)
    pending_limit: int = Field(strict=True, ge=1)
    concurrency: int = Field(strict=True, ge=1)
    shutdown_seconds: float = Field(gt=0, allow_inf_nan=False)
    record_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    result_max_length: int = Field(strict=True, ge=1)
    tenant_lease_seconds: float = Field(gt=0, allow_inf_nan=False)
    max_jobs: int = Field(strict=True, ge=1)
    max_retry_seconds: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_lease(self):
        if self.owner_renew_seconds + self.command_timeout_seconds >= self.owner_lease_seconds:
            raise ValueError("续租周期和命令上界必须小于 owner 租约")
        return self

    def owner_key(self):
        return CacheKey(key="job:owner", remark="调度 owner 租约", client_name=self.cache_client)
