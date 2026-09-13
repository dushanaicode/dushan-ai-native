from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from redis.asyncio import Redis

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_read_result import CacheReadResult
from framework.starter_di.decorators.inject import Inject


class BaseCacheDAO:
    """业务缓存 DAO 的基类：把某一个 CacheKey 的读写收敛到一处。

    子类在构造时绑定自己的 CacheKey，之后只传业务标识；需要 Redis 原生数据结构
    （列表、集合、有序集合等）时用 get_client() 取客户端自行操作，
    但键仍要用 build_full_key() 生成，避免绕开前缀声明写出野键。

    基类本身不加 DI 标记：它的构造参数是业务声明的 CacheKey，容器无法也不应该去解析。
    子类自己声明 @dao 并提供无参构造：

        @dao
        class UserCacheDAO(BaseCacheDAO):
            def __init__(self) -> None:
                super().__init__(SystemCacheKeys.USER)
    """

    _cache_handler: CacheHandler = Inject()

    def __init__(self, cache_key: CacheKey) -> None:
        self._cache_key = cache_key

    @property
    def cache_key(self) -> CacheKey:
        """本 DAO 绑定的键声明。"""
        return self._cache_key

    def get_client(self) -> Redis:
        """取得该前缀所属的 Redis 客户端。"""
        return self._cache_handler.get_client(self._cache_key)

    def build_full_key(self, identifier: str) -> str:
        """构造物理键。"""
        return self._cache_handler.build_full_key(self._cache_key, identifier)

    async def get(self, identifier: str) -> CacheReadResult[Any]:
        """读取一个键，保留命中空值与未命中的区别。"""
        return await self._cache_handler.get(self._cache_key, identifier)

    async def set(self, identifier: str, value: Any, ttl_seconds: int | None = None) -> None:
        """写入一个值。"""
        await self._cache_handler.set(self._cache_key, identifier, value, ttl_seconds)

    async def get_and_delete(self, identifier: str) -> CacheReadResult[Any]:
        """原子消费一次性值。"""
        return await self._cache_handler.get_and_delete(self._cache_key, identifier)

    async def delete(self, identifier: str) -> int:
        """删除一个键。"""
        return await self._cache_handler.delete(self._cache_key, identifier)

    async def delete_many(self, identifiers: Iterable[str]) -> int:
        """批量删除确定标识。"""
        return await self._cache_handler.delete_many(self._cache_key, identifiers)

    async def delete_all(self) -> int:
        """删除本前缀下的全部键。"""
        return await self._cache_handler.delete_all(self._cache_key)

    async def get_or_load(
        self,
        identifier: str,
        loader: Callable[[], Awaitable[Any]],
        ttl_seconds: int | None = None,
    ) -> Any:
        """命中返回缓存，未命中回源一次并发布结果。"""
        return await self._cache_handler.get_or_load(
            self._cache_key, identifier, loader, ttl_seconds
        )
