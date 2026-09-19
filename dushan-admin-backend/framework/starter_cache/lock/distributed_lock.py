import asyncio
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.definitions.constants.cache_constants import CacheConstants
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.definitions.constants.cache_lock_defaults import CacheLockDefaults
from framework.starter_cache.definitions.enums.lock_release_outcome_enum import (
    LockReleaseOutcomeEnum,
)
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.lock.redis_lease_lock import RedisLeaseLock
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject


@framework
class DistributedLock:
    """基于 Redis 租约的分布式互斥入口。

    with_lock 会强制给临界区设定执行上界，并保证退出时一定尝试释放；
    释放终态不是 RELEASED（锁已过期或被别人接管）时明确报错，不当作成功。
    锁是不可重入的：同一任务再次进入同名锁会一直等到超时。
    """

    _cache_manager: CacheManager = Inject()

    def build_lock_key(self, lock_name: str) -> str:
        """锁键使用独立前缀，不与任何业务 CacheKey 前缀重叠。"""
        if not isinstance(lock_name, str) or not lock_name.strip():
            raise CacheException(CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg="锁名称不能为空")
        return f"{CacheConstants.DISTRIBUTED_LOCK_KEY_PREFIX}{lock_name}"

    async def acquire(
        self,
        lock_name: str,
        *,
        lease_seconds: float = CacheLockDefaults.LEASE_SECONDS,
        wait_seconds: float = CacheLockDefaults.WAIT_SECONDS,
        client_name: str | None = None,
    ) -> RedisLeaseLock | None:
        """获取租约；等待上界内没拿到返回 None，由调用方决定如何降级。"""
        lock = RedisLeaseLock(
            self._resolve_client(client_name),
            self.build_lock_key(lock_name),
            lease_seconds=lease_seconds,
            wait_seconds=wait_seconds,
        )
        return lock if await lock.acquire() else None

    @staticmethod
    async def release(lock: RedisLeaseLock) -> LockReleaseOutcomeEnum:
        """释放已获取的租约并返回原子终态。"""
        return await lock.release()

    def with_lock(
        self,
        lock_name: str,
        *,
        lease_seconds: float = CacheLockDefaults.LEASE_SECONDS,
        wait_seconds: float = CacheLockDefaults.WAIT_SECONDS,
        critical_section_timeout_seconds: float = CacheLockDefaults.CRITICAL_SECTION_TIMEOUT_SECONDS,
        client_name: str | None = None,
    ) -> AbstractAsyncContextManager[None]:
        """返回带执行上界的异步锁上下文；参数在进入前就完成校验。"""
        timing = self.validate_timing(lease_seconds, wait_seconds, critical_section_timeout_seconds)
        return self._with_lock(lock_name, *timing, client_name)

    @asynccontextmanager
    async def _with_lock(
        self,
        lock_name: str,
        lease_seconds: float,
        wait_seconds: float,
        critical_section_timeout_seconds: float,
        client_name: str | None,
    ):
        """获取租约、限制临界区时长，并在任何终态下释放本次持有的锁。"""
        lock = await self.acquire(
            lock_name,
            lease_seconds=lease_seconds,
            wait_seconds=wait_seconds,
            client_name=client_name,
        )
        if lock is None:
            raise CacheException(
                CacheErrorCodes.LOCK_CONTENDED, msg=f"无法获取分布式锁：{lock_name}"
            )
        primary_error: BaseException | None = None
        try:
            async with asyncio.timeout_at(
                lock.get_critical_deadline(critical_section_timeout_seconds)
            ):
                yield
        except BaseException as error:
            primary_error = error
            raise
        finally:
            try:
                outcome = await self.release(lock)
                if outcome is not LockReleaseOutcomeEnum.RELEASED:
                    raise CacheException(
                        CacheErrorCodes.LOCK_RELEASE_FAILED,
                        msg=f"分布式锁 {lock_name} 释放终态为 {outcome.code}",
                    )
            except BaseException as release_error:
                # 临界区本身已经失败时，释放失败作为附注保留，不覆盖真正的业务原因。
                if primary_error is None or release_error is primary_error:
                    raise
                primary_error.add_note(
                    f"分布式锁释放失败：{type(release_error).__name__}: {release_error}"
                )

    def _resolve_client(self, client_name: str | None):
        """锁默认落在配置声明的默认客户端，调用方也可以指定。"""
        try:
            if client_name is None:
                return self._cache_manager.get_default_client()
            return self._cache_manager.get_client(client_name)
        except Exception as error:
            raise CacheException(
                CacheErrorCodes.CLIENT_NOT_FOUND,
                msg=f"无法获取分布式锁使用的缓存客户端：{client_name}",
                cause=error,
            ) from error

    @staticmethod
    def validate_timing(
        lease_seconds: float, wait_seconds: float, critical_section_timeout_seconds: float
    ) -> tuple[float, float, float]:
        """临界区上界必须严格小于租约，否则锁可能在业务跑完前就过期。"""
        lease = RedisLeaseLock.validate_seconds(lease_seconds, "lease_seconds", allow_zero=False)
        wait = RedisLeaseLock.validate_seconds(wait_seconds, "wait_seconds", allow_zero=True)
        critical = RedisLeaseLock.validate_seconds(
            critical_section_timeout_seconds, "critical_section_timeout_seconds", allow_zero=False
        )
        if critical >= lease:
            raise CacheException(
                CacheErrorCodes.LOCK_ACQUIRE_FAILED,
                msg="critical_section_timeout_seconds 必须小于 lease_seconds",
            )
        return lease, wait, critical
