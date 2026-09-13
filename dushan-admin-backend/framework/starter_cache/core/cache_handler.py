from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.constants.cache_lock_defaults import CacheLockDefaults
from framework.starter_cache.core.cache_generation_coordinator import CacheGenerationCoordinator
from framework.starter_cache.core.cache_generation_publisher import CacheGenerationPublisher
from framework.starter_cache.core.cache_key_deleter import CacheKeyDeleter
from framework.starter_cache.core.cache_key_resolver import CacheKeyResolver
from framework.starter_cache.core.cache_load_through_coordinator import CacheLoadThroughCoordinator
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.core.cache_serializer import CacheSerializer
from framework.starter_cache.exception.cache_config_exception import CacheConfigException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_operation_exception import CacheOperationException
from framework.starter_cache.model.cache_generation_state import CacheGenerationState
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_read_result import CacheReadResult
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject


@framework
class CacheHandler:
    """缓存读写、删除与回源的统一入口。

    所有方法都以 CacheKey 对象为参数，客户端和默认 TTL 直接来自这个声明，
    因此不存在"前缀写对了但路由到别的库"的调用方式。

    未命中与空值是两种结果：get 返回 CacheReadResult，命中的 None 表示这是一次
    防穿透写入的空值，调用方不应再回源。所有 Redis 失败都会抛出缓存异常并保留原始
    RedisError，既不会静默吞掉，也不会自动重试。
    """

    _settings: CacheSettings = Inject()
    _cache_manager: CacheManager = Inject()
    _serializer: CacheSerializer = Inject()
    _publisher: CacheGenerationPublisher = Inject()
    _coordinator: CacheGenerationCoordinator = Inject()
    _deleter: CacheKeyDeleter = Inject()
    _load_through: CacheLoadThroughCoordinator = Inject()

    def get_client(self, cache_key: CacheKey) -> Redis:
        """取得该 CacheKey 声明的客户端，供需要原生命令的专用 DAO 使用。"""
        return self._cache_manager.get_client(cache_key.client_name)

    async def eval_atomic(
        self,
        cache_key: CacheKey,
        identifiers: tuple[str, ...],
        script: str,
        args: tuple[str | int, ...] = (),
    ) -> Any:
        """在同一客户端原子执行受信任的内部 Lua；调用方负责专用数据格式和 TTL。

        不与 get/set 的序列化值混用。脚本、参数及返回值均不得写日志。
        """
        client = self.get_client(cache_key)
        keys = tuple(self.build_full_key(cache_key, identifier) for identifier in identifiers)
        try:
            return await client.eval(script, len(keys), *keys, *args)
        except RedisError as error:
            raise CacheOperationException(msg="Redis 原子操作失败", cause=error) from error

    @staticmethod
    def build_full_key(cache_key: CacheKey, identifier: str) -> str:
        """构造物理键，便于调用方记录日志或自行组织批量操作。"""
        return CacheKeyResolver.build_full_key(cache_key, identifier)

    async def get(self, cache_key: CacheKey, identifier: str) -> CacheReadResult[Any]:
        """读取一个键；命中的空值会明确标记为命中。"""
        client = self.get_client(cache_key)
        full_key = CacheKeyResolver.build_full_key(cache_key, identifier)
        hit, payload = await self._publisher.read(client, full_key)
        if not hit:
            return CacheReadResult[Any](hit=False)
        return CacheReadResult[Any](hit=True, value=self._serializer.deserialize(payload))

    async def set(
        self, cache_key: CacheKey, identifier: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        """直接写入一个值；调用方明确知道自己在覆盖，不参与 generation 协议。"""
        client = self.get_client(cache_key)
        full_key = CacheKeyResolver.build_full_key(cache_key, identifier)
        await self._publisher.set_direct(
            client,
            full_key,
            self._serializer.serialize(value),
            self.resolve_ttl_seconds(cache_key, ttl_seconds),
        )

    async def get_and_delete(self, cache_key: CacheKey, identifier: str) -> CacheReadResult[Any]:
        """原子消费一次性值；未命中和已被作废的值都返回未命中。"""
        client = self.get_client(cache_key)
        full_key = CacheKeyResolver.build_full_key(cache_key, identifier)
        try:
            raw = await client.getdel(full_key)
        except RedisError as error:
            raise CacheOperationException(msg="Redis GETDEL 操作失败", cause=error) from error
        if raw is None:
            return CacheReadResult[Any](hit=False)
        is_current, payload = await self._publisher.decode_if_current(client, raw)
        if not is_current:
            return CacheReadResult[Any](hit=False)
        return CacheReadResult[Any](hit=True, value=self._serializer.deserialize(payload))

    async def delete(self, cache_key: CacheKey, identifier: str) -> int:
        """删除一个键，并在 generation 栅栏内执行，挡住同时在跑的回源写入。"""
        client = self.get_client(cache_key)
        full_key = CacheKeyResolver.build_full_key(cache_key, identifier)
        return await self._run_invalidation(
            client, cache_key, lambda: self._deleter.delete_keys(client, (full_key,))
        )

    async def delete_many(self, cache_key: CacheKey, identifiers: Iterable[str]) -> int:
        """批量删除确定标识；空输入是合法的零删除。"""
        full_keys = [
            CacheKeyResolver.build_full_key(cache_key, identifier) for identifier in identifiers
        ]
        if not full_keys:
            return 0
        client = self.get_client(cache_key)
        return await self._run_invalidation(
            client, cache_key, lambda: self._deleter.delete_keys(client, full_keys)
        )

    async def delete_all(self, cache_key: CacheKey) -> int:
        """删除该前缀下的全部键。"""
        client = self.get_client(cache_key)
        pattern = CacheKeyResolver.build_prefix_pattern(cache_key)
        return await self._run_invalidation(
            client, cache_key, lambda: self._deleter.delete_matching(client, pattern)
        )

    async def get_or_load(
        self,
        cache_key: CacheKey,
        identifier: str,
        loader: Callable[[], Awaitable[Any]],
        ttl_seconds: int | None = None,
        *,
        use_lock: bool = True,
        lease_seconds: float = CacheLockDefaults.LEASE_SECONDS,
        wait_seconds: float = CacheLockDefaults.WAIT_SECONDS,
        critical_section_timeout_seconds: float = CacheLockDefaults.CRITICAL_SECTION_TIMEOUT_SECONDS,
    ) -> Any:
        """命中则返回缓存值，未命中则回源一次并按 generation 协议发布结果。"""
        full_key = CacheKeyResolver.build_full_key(cache_key, identifier)
        return await self._load_through.get_or_load(
            full_key=full_key,
            read=lambda: self.get(cache_key, identifier),
            delete_corrupted=lambda: self.delete(cache_key, identifier),
            load_and_publish=lambda: self._load_and_publish(
                cache_key, identifier, loader, ttl_seconds
            ),
            client_name=cache_key.client_name,
            use_lock=use_lock,
            lease_seconds=lease_seconds,
            wait_seconds=wait_seconds,
            critical_section_timeout_seconds=critical_section_timeout_seconds,
        )

    async def capture_generation(self, cache_key: CacheKey) -> tuple[CacheGenerationState, ...]:
        """记录当前 generation 快照。

        调用方需要自己控制回源时序时（例如 TTL 来自上游返回的过期时间），
        按 capture_generation → 自行取数 → publish_loaded_value 的顺序使用；
        中途发生失效时 publish_loaded_value 返回 False 并撤销自己写入的值。
        """
        return await self._coordinator.capture_snapshot(self.get_client(cache_key), cache_key)

    def resolve_ttl_seconds(self, cache_key: CacheKey, ttl_seconds: int | None) -> int | None:
        """确定本次写入的存活时间：显式参数优先，其次是键声明的默认值。

        None 表示不设置过期。0 和负数不是"永久"而是明确的配置错误，
        因为它们通常来自未初始化的变量；超过 max_ttl_seconds 同样直接拒绝，
        避免一次写入长期占用内存。
        """
        effective = cache_key.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if effective is None:
            return None
        if type(effective) is not int or effective <= 0:
            raise CacheConfigException(
                error_code=CacheErrorCodes.CONFIG_ERROR, msg="缓存 TTL 必须是正整数秒或 None"
            )
        if effective > self._settings.max_ttl_seconds:
            raise CacheConfigException(
                error_code=CacheErrorCodes.CONFIG_ERROR,
                msg=f"缓存 TTL {effective} 秒超过上限 {self._settings.max_ttl_seconds} 秒",
            )
        return effective

    async def publish_loaded_value(
        self,
        cache_key: CacheKey,
        identifier: str,
        value: Any,
        snapshot: tuple[CacheGenerationState, ...],
        ttl_seconds: int | None = None,
    ) -> bool:
        """按防穿透策略发布一次回源结果，返回是否真正写入。

        返回 False 有两种原因：快照期间发生过失效（值已被自己撤销），
        或结果为空且关闭了空值缓存。两种情况都不是错误，调用方照常返回业务结果。
        """
        should_publish, publication_ttl = self._resolve_publication_ttl(
            cache_key, value, ttl_seconds
        )
        if not should_publish:
            return False
        return await self._publisher.publish(
            self.get_client(cache_key),
            CacheKeyResolver.build_full_key(cache_key, identifier),
            self._serializer.serialize(value),
            publication_ttl,
            snapshot,
        )

    async def _load_and_publish(
        self,
        cache_key: CacheKey,
        identifier: str,
        loader: Callable[[], Awaitable[Any]],
        ttl_seconds: int | None,
    ) -> Any:
        """先记录 generation，再回源，最后只发布仍然有效的结果。"""
        snapshot = await self.capture_generation(cache_key)
        value = await loader()
        await self.publish_loaded_value(cache_key, identifier, value, snapshot, ttl_seconds)
        return value

    def _resolve_publication_ttl(
        self, cache_key: CacheKey, value: Any, ttl_seconds: int | None
    ) -> tuple[bool, int | None]:
        """空值按防穿透配置决定是否写入，并使用独立的较短 TTL。"""
        if value is not None:
            return True, self.resolve_ttl_seconds(cache_key, ttl_seconds)
        if not self._settings.null_value_enabled:
            return False, None
        return True, self._settings.null_value_ttl_seconds

    async def _run_invalidation(
        self, client: Redis, cache_key: CacheKey, operation: Callable[[], Awaitable[int]]
    ) -> int:
        """把一次删除放进 generation 栅栏：开始失效 → 删除 → 结束失效。

        栅栏保证期间正在回源的请求即使写入成功也会立刻撤销自己的结果，
        因此删除返回后，同前缀不会再出现基于旧数据的缓存值。
        """
        generation_key = self._coordinator.build_generation_key(cache_key)
        generation = await self._coordinator.begin(client, generation_key)
        deleted = await operation()
        await self._coordinator.finalize(client, generation)
        return deleted
