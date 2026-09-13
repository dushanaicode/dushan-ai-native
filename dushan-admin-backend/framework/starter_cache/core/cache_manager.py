import asyncio
from threading import RLock

from loguru import logger
from redis.asyncio import Redis

from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.core.cache_resource_snapshot import CacheResourceSnapshot
from framework.starter_cache.core.redis_client_factory import RedisClientFactory
from framework.starter_cache.enums.cache_lifecycle_phase_enum import CacheLifecyclePhaseEnum
from framework.starter_cache.exception.cache_config_exception import CacheConfigException
from framework.starter_cache.exception.cache_connection_exception import CacheConnectionException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject


@framework
class CacheManager:
    """按应用持有全部 Redis 客户端与连接池，并以原子快照管理它们的生命周期。

    客户端只有在整代资源全部创建并探活成功后才对外可见；任何一步失败都会反向
    关闭已创建的资源。关闭失败的引用继续由本实例保留，下次关闭时重试，
    不会被丢弃成无法回收的连接。实例由容器按应用创建，没有类级共享状态。
    """

    _settings: CacheSettings = Inject()
    _factory: RedisClientFactory = Inject()

    def __init__(self) -> None:
        self._lifecycle_lock = asyncio.Lock()
        self._state_lock = RLock()
        self._phase = CacheLifecyclePhaseEnum.STOPPED
        self._active = CacheResourceSnapshot()
        self._pending_close = CacheResourceSnapshot()

    @property
    def is_ready(self) -> bool:
        """只有完整提交的资源快照才算可用。"""
        with self._state_lock:
            return self._phase is CacheLifecyclePhaseEnum.READY

    @property
    def phase(self) -> CacheLifecyclePhaseEnum:
        """返回当前生命周期阶段，供启动器和诊断读取。"""
        with self._state_lock:
            return self._phase

    async def open(self) -> None:
        """创建并探活配置声明的全部客户端，成功后一次提交资源快照。"""
        async with self._lifecycle_lock:
            with self._state_lock:
                if self._phase is CacheLifecyclePhaseEnum.READY:
                    return
                if self._phase is CacheLifecyclePhaseEnum.CLOSE_FAILED:
                    raise CacheConnectionException(
                        error_code=CacheErrorCodes.INIT_FAILED,
                        msg="缓存资源上次关闭失败，必须先重试关闭",
                    )
                self._phase = CacheLifecyclePhaseEnum.INITIALIZING
            if not self._settings.clients:
                with self._state_lock:
                    self._phase = CacheLifecyclePhaseEnum.STOPPED
                raise CacheConfigException(msg="缓存客户端配置不能为空")

            staging = CacheResourceSnapshot()
            try:
                await self._create_clients(staging)
            except BaseException as error:
                await self._rollback(staging, error)
            with self._state_lock:
                self._active = staging
                self._phase = CacheLifecyclePhaseEnum.READY
            logger.info("缓存连接就绪，客户端 {} 个", len(staging.clients))

    async def _create_clients(self, staging: CacheResourceSnapshot) -> None:
        """按声明顺序创建资源，先登记所有权再探活，取消也不会丢失引用。"""
        for client_settings in self._settings.clients:
            pool = self._factory.create_pool(self._settings, client_settings)
            staging.pools[client_settings.name] = pool
            client = self._factory.create_client(pool)
            staging.clients[client_settings.name] = client
            await self._factory.require_ping(client)

    async def _rollback(self, staging: CacheResourceSnapshot, error: BaseException) -> None:
        """启动失败时反向清理未提交资源，并保留清理失败的引用。"""
        failed, cleanup_errors = await self._close_snapshot(staging)
        with self._state_lock:
            self._pending_close = failed
            self._phase = (
                CacheLifecyclePhaseEnum.CLOSE_FAILED
                if cleanup_errors
                else CacheLifecyclePhaseEnum.STOPPED
            )
        if cleanup_errors:
            raise BaseExceptionGroup("缓存初始化失败且资源清理失败", [error, *cleanup_errors])
        if isinstance(error, (CacheConfigException, CacheConnectionException)):
            raise error
        if isinstance(error, Exception):
            raise CacheConnectionException(
                error_code=CacheErrorCodes.INIT_FAILED, msg="缓存初始化失败", cause=error
            ) from error
        raise error

    def get_client(self, client_name: str) -> Redis:
        """从当前 READY 快照读取客户端；未就绪或名称未声明都明确失败。"""
        with self._state_lock:
            if self._phase is not CacheLifecyclePhaseEnum.READY:
                raise CacheConnectionException(
                    error_code=CacheErrorCodes.NOT_INITIALIZED,
                    msg=f"缓存当前不可用：{self._phase.code}",
                )
            client = self._active.clients.get(client_name)
        if client is None:
            raise CacheConnectionException(
                error_code=CacheErrorCodes.CLIENT_NOT_FOUND,
                msg=f"未找到缓存客户端：{client_name}",
            )
        return client

    def get_default_client(self) -> Redis:
        """读取配置声明的默认客户端，供分布式锁等没有业务前缀的场景使用。"""
        return self.get_client(self._settings.default_client)

    async def close(self) -> None:
        """先撤销可见性，再关闭整代资源；关闭失败的引用留到下次重试。"""
        async with self._lifecycle_lock:
            with self._state_lock:
                if self._phase is CacheLifecyclePhaseEnum.STOPPED and self._pending_close.is_empty:
                    return
                self._phase = CacheLifecyclePhaseEnum.CLOSING
                resources = self._pending_close.merge(self._active)
                self._active = CacheResourceSnapshot()
                self._pending_close = CacheResourceSnapshot()

            failed, errors = await self._close_snapshot(resources)
            with self._state_lock:
                self._pending_close = failed
                self._phase = (
                    CacheLifecyclePhaseEnum.CLOSE_FAILED
                    if errors
                    else CacheLifecyclePhaseEnum.STOPPED
                )
            if errors:
                if len(errors) == 1:
                    raise errors[0]
                raise BaseExceptionGroup("缓存资源关闭失败", errors)
            logger.info("缓存连接已全部关闭")

    @staticmethod
    async def _close_snapshot(
        resources: CacheResourceSnapshot,
    ) -> tuple[CacheResourceSnapshot, list[BaseException]]:
        """逐个关闭客户端和连接池，返回仍需重试的引用与全部失败原因。"""
        failed = CacheResourceSnapshot()
        errors: list[BaseException] = []
        for name, client in reversed(tuple(resources.clients.items())):
            try:
                await client.aclose()
            except BaseException as error:
                failed.clients[name] = client
                errors.append(error)
        for name, pool in reversed(tuple(resources.pools.items())):
            try:
                await pool.disconnect(inuse_connections=True)
            except BaseException as error:
                failed.pools[name] = pool
                errors.append(error)
        return failed, errors
