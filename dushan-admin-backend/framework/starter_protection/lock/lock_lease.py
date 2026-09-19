import asyncio
from time import perf_counter

from framework.common.utils.asyncio_utils import AsyncioUtils
from framework.starter_cache.definitions.enums.lock_release_outcome_enum import (
    LockReleaseOutcomeEnum,
)
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.lock.redis_lease_lock import RedisLeaseLock
from framework.starter_protection.core.protection_runtime import ProtectionRuntime


class LockLease:
    """持有单次 Cache 租约；并发或重复关闭共享同一个真实释放终态。"""

    def __init__(self, runtime: ProtectionRuntime, primitive: RedisLeaseLock) -> None:
        self.runtime = runtime
        self.primitive = primitive
        self._close_task: asyncio.Task[LockReleaseOutcomeEnum] | None = None

    async def close(self) -> LockReleaseOutcomeEnum:
        if self._close_task is None:
            self._close_task = asyncio.create_task(self._release(), name="protection-lock-release")
        return await AsyncioUtils.run_cancellation_shielded(self._close_task)

    async def _release(self) -> LockReleaseOutcomeEnum:
        started = perf_counter()
        try:
            async with asyncio.timeout(self.runtime.settings.io_timeout_seconds):
                outcome = await self.primitive.release()
            self.runtime.emit("lock", "release", outcome.code, started)
            return outcome
        except (CacheException, TimeoutError) as error:
            wrapped = self.runtime.unavailable(error)
            self.runtime.emit("lock", "release", wrapped.context["reason"], started)
            raise wrapped from error
        finally:
            self.runtime.leases.discard(self)
