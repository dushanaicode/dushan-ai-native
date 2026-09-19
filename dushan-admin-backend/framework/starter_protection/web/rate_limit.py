from functools import wraps

from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.ratelimiter.rate_limit_rule import RateLimitRule
from framework.starter_protection.web.protection_invocation import (
    ParameterSelector,
    ProtectionInvocation,
    SubjectProvider,
)


def rate_limit(
    operation: str,
    *,
    parameters: ParameterSelector = (),
    subject: SubjectProvider | None = None,
    rules: tuple[RateLimitRule, ...] = (),
):
    """规则顺序扣费，后条拒绝不回滚前条计数；空 rules 使用应用 YAML 规则。"""
    dimensions = [(rule.algorithm, rule.capacity, rule.window_ms) for rule in rules]
    if len(set(dimensions)) != len(dimensions):
        raise ValueError("限流规则不能重复")

    def decorate(func):
        invocation = ProtectionInvocation(func, parameters, subject)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            service, identity, values = invocation.resolve(args, kwargs)
            for rule in rules or (None,):
                decision = await service.rate_limiter.acquire(
                    operation, identity, values, rule=rule
                )
                if not decision.allowed:
                    raise ProtectionException(Codes.RATE_LIMITED, retry_after=decision.retry_after)
            return await func(*args, **kwargs)

        wrapper.__signature__ = invocation.signature
        return wrapper

    return decorate
