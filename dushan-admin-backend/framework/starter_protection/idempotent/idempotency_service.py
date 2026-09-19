from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_protection.core.protection_runtime import ProtectionRuntime
from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.idempotent.idempotency_claim import IdempotencyClaim
from framework.starter_protection.idempotent.idempotency_result import IdempotencyResult
from framework.starter_protection.idempotent.idempotency_rule import IdempotencyRule
from framework.starter_protection.subject.protection_subject import ProtectionSubject


class IdempotencyService:
    """有效期内的重复执行屏障；未知结果及取消保留占位，进程退出后由 TTL 回收。"""

    _ACQUIRE = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
if redis.call('EXISTS', KEYS[1]) == 0 then
    redis.call('HSET', KEYS[1], 'owner', ARGV[1], 'deadline', now + tonumber(ARGV[3]))
    redis.call('PEXPIRE', KEYS[1], ARGV[2])
    return {1, 0}
end
local deadline = tonumber(redis.call('HGET', KEYS[1], 'deadline'))
local ttl = redis.call('PTTL', KEYS[1])
if not deadline or not redis.call('HGET', KEYS[1], 'owner') or ttl < 0 then
    return redis.error_reply('invalid idempotency state')
end
if ARGV[4] == 'sliding' then
    if deadline <= now then
        redis.call('HSET', KEYS[1], 'owner', ARGV[1], 'deadline', now + tonumber(ARGV[3]))
        redis.call('PEXPIRE', KEYS[1], ARGV[2])
        return {1, 0}
    end
    ttl = math.min(tonumber(ARGV[2]), deadline - now)
    redis.call('PEXPIRE', KEYS[1], ttl)
end
return {0, ttl}
"""
    _FINISH = """
if redis.call('EXISTS', KEYS[1]) == 0 then return 'missing' end
if redis.call('HGET', KEYS[1], 'owner') ~= ARGV[1] then return 'not_owner' end
if ARGV[2] == 'release' then
    redis.call('DEL', KEYS[1])
    return 'released'
end
return 'retained'
"""

    def __init__(self, runtime: ProtectionRuntime) -> None:
        self.runtime = runtime

    async def acquire(
        self,
        operation: str,
        subject: ProtectionSubject,
        parameters: object,
        *,
        rule: IdempotencyRule | None = None,
    ) -> IdempotencyResult:
        with self.runtime.operation():
            return await self._acquire(operation, subject, parameters, rule)

    async def _acquire(self, operation, subject, parameters, rule) -> IdempotencyResult:
        runtime = self.runtime
        started = perf_counter()
        if not runtime.enabled("idempotency"):
            runtime.emit("idempotency", "acquire", "disabled", started)
            return IdempotencyResult("disabled")
        rule = runtime.settings.idempotency if rule is None else rule
        # 生命周期配置变化不改变业务键，否则重启或滚动部署会绕过旧占位。
        identifier = "idempotency:" + runtime.identifier(operation, subject, parameters)
        owner = uuid4().hex
        accepted, retry_ms = await runtime.eval(
            "idempotency",
            "acquire",
            identifier,
            self._ACQUIRE,
            (owner, rule.ttl_ms, rule.max_lifetime_ms, rule.mode),
        )
        status = "acquired" if accepted else "duplicate"
        runtime.emit("idempotency", "acquire", status, started)
        return IdempotencyResult(
            status, retry_ms, IdempotencyClaim(identifier, owner, rule) if accepted else None
        )

    async def complete(self, claim: IdempotencyClaim) -> str:
        with self.runtime.operation():
            return await self._finish(
                claim, "release" if claim.rule.mode == "delete_on_complete" else "retain"
            )

    async def fail(self, claim: IdempotencyClaim, *, known_no_effect: bool) -> str:
        """known_no_effect 只能由确认没有业务副作用的调用方设置；未知结果不写 Redis。"""
        with self.runtime.operation():
            if not known_no_effect:
                return "retained"
            return await self._finish(claim, claim.rule.failure_action)

    async def _finish(self, claim: IdempotencyClaim, action: str) -> str:
        started = perf_counter()
        outcome = await self.runtime.eval(
            "idempotency", action, claim.identifier, self._FINISH, (claim.owner, action)
        )
        self.runtime.emit("idempotency", action, outcome, started)
        return outcome

    @asynccontextmanager
    async def guard(
        self,
        operation: str,
        subject: ProtectionSubject,
        parameters: object,
        *,
        rule: IdempotencyRule | None = None,
        release_on: tuple[type[Exception], ...] = (),
    ):
        """只对 release_on 中显式声明的无副作用异常应用 failure_action；取消始终保留。"""
        if any(not issubclass(kind, Exception) or kind is Exception for kind in release_on):
            raise ValueError("release_on 必须列出具体的无副作用异常类型")
        with self.runtime.operation():
            acquired = await self._acquire(operation, subject, parameters, rule)
            if acquired.status == "duplicate":
                raise ProtectionException(Codes.DUPLICATE, retry_after=acquired.retry_after)
            claim = acquired.claim
            action = None
            primary = None
            try:
                yield claim
            except BaseException as error:
                primary = error
                if isinstance(error, release_on) and claim is not None:
                    action = claim.rule.failure_action
            else:
                if claim is not None:
                    action = "release" if claim.rule.mode == "delete_on_complete" else "retain"
            finally:
                cleanup_error, cancellation = None, None
                if action is not None:

                    async def finish():
                        outcome = await self._finish(claim, action)
                        if outcome in ("missing", "not_owner"):
                            raise ProtectionException(Codes.OWNER_LOST)

                    cleanup_error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                        finish, "幂等状态完成"
                    )
                if primary is None and cancellation is None and cleanup_error is not None:
                    raise cleanup_error
                CleanupUtils.raise_collected_cleanup_errors(
                    "幂等业务及清理",
                    [] if cleanup_error is None else [cleanup_error],
                    primary_error=primary,
                    caller_cancellation=cancellation,
                )
