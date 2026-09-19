import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from framework.starter_cache.definitions.constants.cache_constants import CacheConstants
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.definitions.constants.cache_lock_defaults import CacheLockDefaults
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.lock.distributed_lock import DistributedLock
from framework.starter_cache.model.cache_read_result import CacheReadResult
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject

# 只有内容无法解析才删键重载，其余缓存故障必须原样上抛。
_CORRUPTED_CODES = (
    CacheErrorCodes.SERIALIZATION_FAILED,
    CacheErrorCodes.DESERIALIZATION_FAILED,
)


@framework
class CacheLoadThroughCoordinator:
    """把同一个键的并发回源收敛成一次，跨进程再用 Redis 锁收敛成一次。

    两层收敛解决不同的问题：进程内的 in-flight 表避免同一个应用重复查库；
    分布式锁避免多副本同时把同一个热点键打到数据库上。锁竞争失败时先重读一次缓存，
    因为持锁者往往已经把值写好了；仍然没有才把竞争异常抛给调用方，
    由调用方决定退避还是降级，这里不会静默重试。

    in-flight 表是实例状态，随应用容器创建和销毁，不同应用互不影响。
    """

    _distributed_lock: DistributedLock = Inject()

    def __init__(self) -> None:
        self._registry_lock = asyncio.Lock()
        self._in_flight: dict[str, asyncio.Task[Any]] = {}

    async def get_or_load(
        self,
        *,
        full_key: str,
        read: Callable[[], Awaitable[CacheReadResult[Any]]],
        delete_corrupted: Callable[[], Awaitable[Any]],
        load_and_publish: Callable[[], Awaitable[Any]],
        client_name: str,
        use_lock: bool = True,
        lease_seconds: float = CacheLockDefaults.LEASE_SECONDS,
        wait_seconds: float = CacheLockDefaults.WAIT_SECONDS,
        critical_section_timeout_seconds: float = CacheLockDefaults.CRITICAL_SECTION_TIMEOUT_SECONDS,
    ) -> Any:
        """命中直接返回；未命中时同键至多执行一个共享回源任务。"""
        if use_lock:
            lease_seconds, wait_seconds, critical_section_timeout_seconds = (
                DistributedLock.validate_timing(
                    lease_seconds, wait_seconds, critical_section_timeout_seconds
                )
            )
        flight_key = f"{client_name}\x00{full_key}"
        return await self._run_single_flight(
            flight_key,
            lambda: self._read_or_load(
                full_key,
                read,
                delete_corrupted,
                load_and_publish,
                client_name,
                use_lock,
                lease_seconds,
                wait_seconds,
                critical_section_timeout_seconds,
            ),
        )

    async def _run_single_flight(
        self, flight_key: str, operation: Callable[[], Awaitable[Any]]
    ) -> Any:
        """同键只有第一个调用者真正执行，其余等待同一个任务的结果。"""
        task, is_owner = await self._get_or_create_flight(flight_key, operation)
        try:
            if is_owner:
                return await task
            # 搭车者的取消不能连带取消正在回源的共享任务。
            return await asyncio.shield(task)
        finally:
            if is_owner:
                await self._remove_flight(flight_key, task)

    async def _get_or_create_flight(
        self, flight_key: str, operation: Callable[[], Awaitable[Any]]
    ) -> tuple[asyncio.Task[Any], bool]:
        async with self._registry_lock:
            existing = self._in_flight.get(flight_key)
            if existing is not None:
                return existing, False
            task = asyncio.create_task(operation(), name="cache-load-through")
            self._in_flight[flight_key] = task
            return task, True

    async def _remove_flight(self, flight_key: str, task: asyncio.Task[Any]) -> None:
        async with self._registry_lock:
            if self._in_flight.get(flight_key) is task:
                del self._in_flight[flight_key]

    async def _read_or_load(
        self,
        full_key: str,
        read: Callable[[], Awaitable[CacheReadResult[Any]]],
        delete_corrupted: Callable[[], Awaitable[Any]],
        load_and_publish: Callable[[], Awaitable[Any]],
        client_name: str,
        use_lock: bool,
        lease_seconds: float,
        wait_seconds: float,
        critical_section_timeout_seconds: float,
    ) -> Any:
        """先读一次缓存；未命中或内容损坏时按是否加锁走不同的回源路径。"""
        try:
            cached = await read()
        except CacheException as error:
            if error.error_code not in _CORRUPTED_CODES:
                raise
            if not use_lock:
                await delete_corrupted()
                return await load_and_publish()
        else:
            if cached.hit:
                return cached.value
            if not use_lock:
                return await load_and_publish()

        return await self._load_with_lock(
            full_key,
            read,
            delete_corrupted,
            load_and_publish,
            client_name,
            lease_seconds,
            wait_seconds,
            critical_section_timeout_seconds,
        )

    async def _load_with_lock(
        self,
        full_key: str,
        read: Callable[[], Awaitable[CacheReadResult[Any]]],
        delete_corrupted: Callable[[], Awaitable[Any]],
        load_and_publish: Callable[[], Awaitable[Any]],
        client_name: str,
        lease_seconds: float,
        wait_seconds: float,
        critical_section_timeout_seconds: float,
    ) -> Any:
        """持锁后再读一次，确认确实需要回源才去查数据源。"""
        lock_entered = False
        try:
            async with self._distributed_lock.with_lock(
                f"{CacheConstants.LOAD_THROUGH_LOCK_PREFIX}:{client_name}:{full_key}",
                lease_seconds=lease_seconds,
                wait_seconds=wait_seconds,
                critical_section_timeout_seconds=critical_section_timeout_seconds,
                client_name=client_name,
            ):
                lock_entered = True
                cached = await self._read_and_drop_corrupted(read, delete_corrupted)
                if cached.hit:
                    return cached.value
                return await load_and_publish()
        except CacheException as error:
            if error.error_code != CacheErrorCodes.LOCK_CONTENDED:
                raise
            # 已经进入临界区后再出现竞争异常属于释放阶段的问题，必须原样上抛。
            if lock_entered:
                raise
            final = await read()
            if final.hit:
                return final.value
            raise

    @staticmethod
    async def _read_and_drop_corrupted(
        read: Callable[[], Awaitable[CacheReadResult[Any]]],
        delete_corrupted: Callable[[], Awaitable[Any]],
    ) -> CacheReadResult[Any]:
        """读到无法解析的内容时删掉它并按未命中处理，避免整段前缀被毒化。"""
        try:
            return await read()
        except CacheException as error:
            if error.error_code not in _CORRUPTED_CODES:
                raise
            await delete_corrupted()
            return CacheReadResult[Any](hit=False)
