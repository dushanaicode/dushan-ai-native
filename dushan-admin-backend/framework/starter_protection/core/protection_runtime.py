import asyncio
from collections.abc import Callable
from contextlib import contextmanager
from time import perf_counter

from loguru import logger
from redis.exceptions import AuthenticationError, AuthorizationError, ConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_protection.config.protection_settings import ProtectionSettings
from framework.starter_protection.core.protection_event import ProtectionEvent
from framework.starter_protection.core.protection_key import ProtectionKey
from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.subject.protection_subject import ProtectionSubject

type ProtectionObserver = Callable[[ProtectionEvent], None]


class ProtectionRuntime:
    """共享 Cache I/O 与应用排空，不共享限流、租约或幂等的状态机。"""

    def __init__(self, settings: ProtectionSettings, cache: CacheHandler) -> None:
        self.settings = settings
        self.cache = cache
        self.key = settings.cache_key()
        self.observer: ProtectionObserver | None = None
        self.state = "new"
        self.active = 0
        self.leases = set()
        self.idle = asyncio.Event()
        self.idle.set()

    def enabled(self, feature: str) -> bool:
        return self.settings.enabled and getattr(self.settings, f"{feature}_enabled")

    @contextmanager
    def operation(self):
        if self.state != "ready":
            raise ProtectionException(Codes.CLOSED)
        if self.active + len(self.leases) >= self.settings.max_inflight:
            raise ProtectionException(Codes.CAPACITY)
        self.active += 1
        self.idle.clear()
        try:
            yield
        finally:
            self.active -= 1
            if self.active == 0:
                self.idle.set()

    def identifier(self, operation: str, subject: ProtectionSubject, parameters: object) -> str:
        try:
            return ProtectionKey.build(operation, subject, parameters, self.settings.max_key_bytes)
        except (TypeError, ValueError) as error:
            raise ProtectionException(Codes.INVALID, cause=error) from error

    async def eval(self, feature: str, action: str, identifier: str, script: str, args=()):
        started = perf_counter()
        try:
            async with asyncio.timeout(self.settings.io_timeout_seconds):
                return await self.cache.eval_atomic(self.key, (identifier,), script, args)
        except (CacheException, TimeoutError) as error:
            wrapped = self.unavailable(error)
            self.emit(feature, action, wrapped.context["reason"], started)
            raise wrapped from error

    @staticmethod
    def unavailable(error: Exception) -> ProtectionException:
        cause = error.__cause__ if isinstance(error, CacheException) else error
        if isinstance(cause, (AuthenticationError, AuthorizationError)):
            reason = "configuration"
        elif isinstance(cause, (TimeoutError, RedisTimeoutError)):
            reason = "timeout"
        elif isinstance(cause, ConnectionError):
            reason = "connection"
        else:
            reason = "command"
        logger.error("保护存储操作失败，分类={}", reason)
        return ProtectionException(Codes.UNAVAILABLE, cause=error, context={"reason": reason})

    def emit(self, feature: str, action: str, outcome: str, started: float) -> None:
        if self.observer is None:
            return
        event = ProtectionEvent(feature, action, outcome, (perf_counter() - started) * 1000)
        try:
            self.observer(event)
        except Exception as error:
            # 观测是可选外部接点；观测器故障有诊断，但不能改变已完成的保护决策。
            logger.warning("保护观测接点失败：{}", type(error).__name__)
