import asyncio
from time import perf_counter

from loguru import logger

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_protection.config.protection_settings import ProtectionSettings
from framework.starter_protection.core.protection_runtime import (
    ProtectionObserver,
    ProtectionRuntime,
)
from framework.starter_protection.exception.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.idempotent.idempotency_service import IdempotencyService
from framework.starter_protection.lock.lock_manager import LockManager
from framework.starter_protection.ratelimiter.rate_limiter import RateLimiter


@framework(scope=ComponentScopeEnum.SINGLETON)
class ProtectionService:
    """每个应用独立装配保护服务；Redis 和连接池始终归 Cache 所有。"""

    def __init__(self, settings: ProtectionSettings, cache: CacheHandler) -> None:
        self.settings = settings
        self.runtime = ProtectionRuntime(settings, cache)
        self.rate_limiter = RateLimiter(self.runtime)
        self.locks = LockManager(self.runtime)
        self.idempotency = IdempotencyService(self.runtime)
        self._close_task: asyncio.Task[None] | None = None

    async def open(self, *, observer: ProtectionObserver | None = None) -> None:
        if self.runtime.state != "new":
            raise ProtectionException(Codes.CLOSED)
        self.runtime.observer = observer
        if self.settings.enabled:
            logger.info("【ProtectionStarter 】开始初始化保护能力")
            # Cache 已探活；此处验证原子脚本权限，不预加载或维护第二份全局 SHA 缓存。
            await self.runtime.eval("protection", "open", "probe", "return 1")
            logger.info("【ProtectionStarter 】Redis 原子脚本权限验证通过")
            logger.info(
                "【ProtectionStarter 】能力装配：限流={}，分布式锁={}，幂等={}",
                self.settings.rate_limit_enabled,
                self.settings.lock_enabled,
                self.settings.idempotency_enabled,
            )
            logger.debug(
                "【ProtectionStarter 】客户端={} 键前缀={} IO超时={}s 最大在途操作={}",
                self.settings.client_name,
                self.settings.key_prefix,
                self.settings.io_timeout_seconds,
                self.settings.max_inflight,
            )
        self.runtime.state = "ready"
        logger.info(
            "【ProtectionStarter 】初始化完成"
            if self.settings.enabled
            else "【ProtectionStarter 】保护能力未启用"
        )

    async def health(self) -> str:
        with self.runtime.operation():
            if not self.settings.enabled:
                return "disabled"
            await self.runtime.eval("protection", "health", "probe", "return 1")
            return "available"

    async def close(self) -> None:
        """停止接收新操作，排空在途业务与租约。取消某个等待者不会取消实际关闭。"""
        if self._close_task is None or self.runtime.state == "close_failed":
            self.runtime.state = "closing"
            self._close_task = asyncio.create_task(self._close(), name="protection-close")
            self._close_task.add_done_callback(self._close_finished)
        await asyncio.shield(self._close_task)

    def _close_finished(self, task: asyncio.Task) -> None:
        if not task.cancelled() and task.exception() is not None:
            logger.error("保护资源关闭失败：{}", type(task.exception()).__name__)
            self.runtime.emit("protection", "close", "failed", perf_counter())

    async def _close(self) -> None:
        try:
            async with asyncio.timeout(self.settings.shutdown_timeout_seconds):
                await self.runtime.idle.wait()
            results = await asyncio.gather(
                *(lease.close() for lease in tuple(self.runtime.leases)), return_exceptions=True
            )
            errors = [result for result in results if isinstance(result, BaseException)]
            if errors:
                raise BaseExceptionGroup("保护租约关闭失败", errors)
        except BaseException:
            self.runtime.state = "close_failed"
            raise
        self.runtime.state = "closed"
        self.runtime.observer = None

    def resources(self) -> dict[str, int | str]:
        return {
            "state": self.runtime.state,
            "active_operations": self.runtime.active,
            "leases": len(self.runtime.leases),
            "closing_tasks": int(self._close_task is not None and not self._close_task.done()),
        }
