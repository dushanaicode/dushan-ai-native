from pydantic import Field

from framework.starter_cache.model.cache_key import CacheKey, CacheKeyName
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_protection.idempotent.idempotency_rule import IdempotencyRule
from framework.starter_protection.lock.lock_rule import LockRule
from framework.starter_protection.ratelimiter.rate_limit_quota import RateLimitQuota
from framework.starter_protection.ratelimiter.rate_limit_rule import RateFailurePolicy


@config_model("protection", env_prefix="PROTECTION_")
class ProtectionSettings(ConfigModel):
    """应用启动快照；部署默认值只由公共 YAML 提供。"""

    enabled: bool
    client_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    key_prefix: CacheKeyName
    io_timeout_seconds: float = Field(gt=0, le=30, allow_inf_nan=False)
    shutdown_timeout_seconds: float = Field(gt=0, le=120, allow_inf_nan=False)
    max_inflight: int = Field(strict=True, ge=1, le=100_000)
    max_key_bytes: int = Field(strict=True, ge=256, le=1_048_576)
    tracing_enabled: bool
    rate_limit_enabled: bool
    rate_limit: RateLimitQuota
    rate_failure_policy: RateFailurePolicy
    circuit_failure_threshold: int = Field(strict=True, ge=1, le=1000)
    circuit_reset_seconds: float = Field(gt=0, le=300, allow_inf_nan=False)
    lock_enabled: bool
    lock: LockRule
    idempotency_enabled: bool
    idempotency: IdempotencyRule

    def cache_key(self) -> CacheKey:
        return CacheKey(
            key=self.key_prefix,
            client_name=self.client_name,
            remark="限流、租约与防重复执行状态",
        )
