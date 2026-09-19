from time import perf_counter
from uuid import uuid4

from loguru import logger

from framework.starter_protection.core.protection_runtime import ProtectionRuntime
from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.ratelimiter.circuit_breaker import CircuitBreaker
from framework.starter_protection.ratelimiter.rate_limit_result import RateLimitResult
from framework.starter_protection.ratelimiter.rate_limit_rule import (
    RateFailurePolicy,
    RateLimitRule,
)
from framework.starter_protection.ratelimiter.rate_reservation import RateReservation
from framework.starter_protection.subject.protection_subject import ProtectionSubject


class RateLimiter:
    """固定窗口从首次成功开始；滑动窗口用 Redis 时间。拒绝不扣额度或延长窗口。"""

    _FIXED = """
local raw = redis.call('GET', KEYS[1])
local count = tonumber(raw or '0')
local ttl = redis.call('PTTL', KEYS[1])
if not count or count < 0 or count ~= math.floor(count) or (raw and ttl < 0) then
    return redis.error_reply('invalid rate state')
end
if count >= tonumber(ARGV[1]) then return {0, ttl} end
redis.call('INCR', KEYS[1])
if not raw then redis.call('PEXPIRE', KEYS[1], ARGV[2]) end
return {1, 0}
"""
    _SLIDING = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
local window = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return {0, tonumber(oldest[2]) + window - now}
end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], window)
return {1, 0}
"""
    _RESERVE = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local first = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return {0, tonumber(first[2]) - now}
end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[3])
redis.call('PEXPIRE', KEYS[1], ARGV[2])
return {1, 0}
"""
    _RELEASE = """
local expiry = redis.call('ZSCORE', KEYS[1], ARGV[1])
if not expiry then return 'not_owner' end
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
redis.call('ZREM', KEYS[1], ARGV[1])
if redis.call('ZCARD', KEYS[1]) == 0 then redis.call('DEL', KEYS[1]) end
if tonumber(expiry) <= now then return 'expired' end
return 'released'
"""

    def __init__(self, runtime: ProtectionRuntime) -> None:
        self.runtime = runtime
        self.circuit = CircuitBreaker(
            runtime.settings.circuit_failure_threshold, runtime.settings.circuit_reset_seconds
        )

    async def acquire(
        self,
        operation: str,
        subject: ProtectionSubject,
        parameters: object = (),
        *,
        rule: RateLimitRule | None = None,
    ) -> RateLimitResult:
        return await self._acquire(operation, subject, parameters, rule, reserve=False)

    async def reserve(
        self,
        operation: str,
        subject: ProtectionSubject,
        parameters: object = (),
        *,
        rule: RateLimitRule | None = None,
    ) -> RateLimitResult:
        """预留最多 capacity 个槽位，每个槽位在 window_ms 后独立到期。"""
        return await self._acquire(operation, subject, parameters, rule, reserve=True)

    async def _acquire(
        self, operation, subject, parameters, rule, *, reserve: bool
    ) -> RateLimitResult:
        runtime = self.runtime
        action = "reserve" if reserve else "acquire"
        started = perf_counter()
        with runtime.operation():
            if not runtime.enabled("rate_limit"):
                runtime.emit("rate_limit", action, "disabled", started)
                return RateLimitResult("disabled")
            policy = runtime.settings.rate_failure_policy
            if rule is None:
                rule = runtime.settings.rate_limit
            elif rule.failure_policy is not None:
                policy = rule.failure_policy
            digest = runtime.identifier(operation, subject, parameters)
            algorithm = "reservation" if reserve else rule.algorithm
            identifier = f"rate:{algorithm}:{rule.capacity}:{rule.window_ms}:{digest}"
            owner = uuid4().hex
            ticket = self.circuit.permit()
            if ticket is None:
                return self._fallback("circuit_open", action, started, policy)
            try:
                script = (
                    self._RESERVE
                    if reserve
                    else self._FIXED
                    if rule.algorithm == "fixed"
                    else self._SLIDING
                )
                accepted, retry_ms = await runtime.eval(
                    "rate_limit", action, identifier, script, (rule.capacity, rule.window_ms, owner)
                )
            except ProtectionException as error:
                reason = error.context["reason"]
                if reason in ("connection", "timeout"):
                    self.circuit.failure(ticket)
                    if policy == "allow":
                        return self._fallback(reason, action, started, policy)
                else:
                    self.circuit.abandon(ticket)
                raise
            except BaseException:
                self.circuit.abandon(ticket)
                raise
            self.circuit.success(ticket)
            status = "acquired" if accepted else "rejected"
            runtime.emit("rate_limit", action, status, started)
            return RateLimitResult(
                status,
                retry_ms,
                RateReservation(identifier, owner) if reserve and accepted else None,
            )

    def _fallback(
        self, reason: str, action: str, started: float, policy: RateFailurePolicy
    ) -> RateLimitResult:
        runtime = self.runtime
        if policy == "block":
            runtime.emit("rate_limit", action, reason, started)
            raise ProtectionException(Codes.UNAVAILABLE, context={"reason": reason})
        logger.warning("限流按显式 allow 策略降级放行，原因={}", reason)
        runtime.emit("rate_limit", action, "degraded", started)
        return RateLimitResult("degraded")

    async def release(self, reservation: RateReservation) -> str:
        """只删除本 owner 的槽位；失效/重复/错误 owner 均不能释放其他持有者。"""
        with self.runtime.operation():
            started = perf_counter()
            outcome = await self.runtime.eval(
                "rate_limit", "release", reservation.identifier, self._RELEASE, (reservation.owner,)
            )
            self.runtime.emit("rate_limit", "release", outcome, started)
            return outcome
