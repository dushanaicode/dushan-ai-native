import asyncio
from contextlib import asynccontextmanager
from time import perf_counter

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_cache.enums.lock_release_outcome_enum import LockReleaseOutcomeEnum
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.lock.redis_lease_lock import RedisLeaseLock
from framework.starter_protection.core.protection_runtime import ProtectionRuntime
from framework.starter_protection.exception.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.lock.lock_lease import LockLease
from framework.starter_protection.lock.lock_rule import LockRule
from framework.starter_protection.subject.protection_subject import ProtectionSubject


class LockManager:
    """复用 Cache 的 owner 校验和租约算法，不可重入，也不运行续租后台任务。"""

    def __init__(self, runtime: ProtectionRuntime) -> None:
        self.runtime = runtime

    async def acquire(
        self,
        operation: str,
        subject: ProtectionSubject,
        parameters: object = (),
        *,
        rule: LockRule | None = None,
    ) -> LockLease | None:
        """竞争超时返回 None；关闭配置的直接获取明确失败，hold 可显式跳过保护。"""
        with self.runtime.operation():
            if not self.runtime.enabled("lock"):
                raise ProtectionException(Codes.CLOSED, msg="分布式锁已配置关闭")
            return await self._acquire(
                operation, subject, parameters, self.runtime.settings.lock if rule is None else rule
            )

    async def _acquire(self, operation, subject, parameters, rule: LockRule) -> LockLease | None:
        runtime = self.runtime
        digest = runtime.identifier(operation, subject, parameters)
        started = perf_counter()
        try:
            primitive = RedisLeaseLock(
                runtime.cache.get_client(runtime.key),
                runtime.cache.build_full_key(runtime.key, f"lock:{digest}"),
                rule.lease_ms / 1000,
                rule.wait_ms / 1000,
                command_timeout_seconds=runtime.settings.io_timeout_seconds,
            )
        except CacheException as error:
            raise runtime.unavailable(error) from error
        lease = LockLease(runtime, primitive)
        task = asyncio.create_task(
            self._bounded_acquire(primitive, rule), name="protection-lock-acquire"
        )
        try:
            acquired = await AsyncioUtils.run_cancellation_shielded(task)
        except BaseException as primary:
            # 调用方取消时先确认 SET 的终态；若实际获取了租约，必须释放后再传播取消。
            if not task.cancelled() and task.exception() is None and task.result():
                error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                    lease.close, "取消后的租约释放"
                )
                CleanupUtils.raise_collected_cleanup_errors(
                    "获取租约期间取消",
                    [] if error is None else [error],
                    primary_error=primary,
                    caller_cancellation=cancellation,
                )
            raise
        if not acquired:
            runtime.emit("lock", "acquire", "busy", started)
            return None
        runtime.leases.add(lease)
        runtime.emit("lock", "acquire", "acquired", started)
        return lease

    async def _bounded_acquire(self, primitive: RedisLeaseLock, rule: LockRule) -> bool:
        try:
            # wait 是竞争预算，单次 I/O 另有上界。基础设施故障不触发获取重试。
            async with asyncio.timeout(
                rule.wait_ms / 1000 + self.runtime.settings.io_timeout_seconds
            ):
                return await primitive.acquire()
        except (CacheException, TimeoutError) as error:
            raise self.runtime.unavailable(error) from error

    @asynccontextmanager
    async def hold(
        self,
        operation: str,
        subject: ProtectionSubject,
        parameters: object = (),
        *,
        rule: LockRule | None = None,
    ):
        """上下文退出会排空释放；租约到期不提供事务回滚或恰好一次保证。"""
        runtime = self.runtime
        with runtime.operation():
            if not runtime.enabled("lock"):
                runtime.emit("lock", "acquire", "disabled", perf_counter())
                yield None
                return
            rule = runtime.settings.lock if rule is None else rule
            lease = await self._acquire(operation, subject, parameters, rule)
            if lease is None:
                raise ProtectionException(Codes.LOCK_BUSY)
            try:
                try:
                    deadline = lease.primitive.get_critical_deadline(
                        rule.execution_timeout_ms / 1000
                    )
                except CacheException as error:
                    raise ProtectionException(Codes.LOCK_LOST, cause=error) from error
                async with asyncio.timeout_at(deadline):
                    yield lease
            except BaseException as error:
                # 必须在此异常仍为当前异常时清理，避免把已转换为 TimeoutError 的
                # 原始 CancelledError 再误认作调用者的新取消信号。
                await self._finish(lease, error)
            else:
                await self._finish(lease, None)

    async def _finish(self, lease: LockLease, primary: BaseException | None) -> None:
        async def release():
            outcome = await lease.close()
            if outcome is not LockReleaseOutcomeEnum.RELEASED:
                raise ProtectionException(Codes.LOCK_LOST)

        error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
            release, "租约上下文释放"
        )
        if primary is None and cancellation is None and error is not None:
            raise error
        CleanupUtils.raise_collected_cleanup_errors(
            "租约上下文结束",
            [] if error is None else [error],
            primary_error=primary,
            caller_cancellation=cancellation,
        )
