from typing import Literal

from framework.starter_protection.ratelimiter.rate_limit_quota import RateLimitQuota

type RateFailurePolicy = Literal["block", "allow"]


class RateLimitRule(RateLimitQuota):
    """窗口以毫秒计；capacity 是突发上限，不排队等待额度。

    failure_policy 只覆盖 Redis 可用性故障的处理；None 表示本规则不覆盖，
    实际策略取应用 YAML 的 rate_failure_policy，不在规则内另设部署默认值。
    """

    failure_policy: RateFailurePolicy | None = None
