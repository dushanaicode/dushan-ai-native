from collections.abc import AsyncIterable, Iterable

from redis.asyncio import Redis
from redis.exceptions import RedisError

from framework.starter_cache.definitions.constants.cache_constants import CacheConstants
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_di.decorators.components import framework

_DELETE_IF_VALUE_MATCHES = """
-- cache_delete_if_value_matches
if redis.call('GET', KEYS[1]) ~= ARGV[1] then
    return 0
end
return redis.call('DEL', KEYS[1])
"""


@framework
class CacheKeyDeleter:
    """以有界批次删除物理键，并对 Redis 的返回形状做严格校验。

    删除统一走单键 DEL 的 pipeline 而不是多键 DEL，这样返回值能逐键核对，
    也让同一份代码在将来接入集群时不会因为跨 slot 直接失败。
    """

    async def delete_keys(self, client: Redis, full_keys: Iterable[str]) -> int:
        """删除同步可迭代对象提供的物理键，返回实际删除数量。"""
        deleted = 0
        chunk: list[str] = []
        try:
            for full_key in full_keys:
                chunk.append(full_key)
                if len(chunk) == CacheConstants.DELETE_CHUNK_SIZE:
                    deleted += await self._delete_chunk(client, chunk)
                    chunk.clear()
            if chunk:
                deleted += await self._delete_chunk(client, chunk)
            return deleted
        except RedisError as error:
            raise CacheException(
                CacheErrorCodes.OPERATION_FAILED, msg="Redis 缓存键删除失败", cause=error
            ) from error

    async def delete_stream(self, client: Redis, full_keys: AsyncIterable[str]) -> int:
        """边扫描边删除，不把整个键集合读进内存。"""
        deleted = 0
        chunk: list[str] = []
        try:
            async for full_key in full_keys:
                chunk.append(full_key)
                if len(chunk) == CacheConstants.DELETE_CHUNK_SIZE:
                    deleted += await self._delete_chunk(client, chunk)
                    chunk.clear()
            if chunk:
                deleted += await self._delete_chunk(client, chunk)
            return deleted
        except RedisError as error:
            raise CacheException(
                CacheErrorCodes.OPERATION_FAILED, msg="Redis 缓存键流式删除失败", cause=error
            ) from error

    async def delete_matching(self, client: Redis, pattern: str) -> int:
        """按模式扫描并删除匹配的物理键。"""
        return await self.delete_stream(
            client, client.scan_iter(match=pattern, count=CacheConstants.SCAN_COUNT)
        )

    @staticmethod
    async def delete_if_value_matches(client: Redis, full_key: str, expected: str | bytes) -> int:
        """只删除值仍然等于 expected 的键，用于发布失败后的自我补偿。"""
        try:
            result = await client.eval(_DELETE_IF_VALUE_MATCHES, 1, full_key, expected)
        except RedisError as error:
            raise CacheException(
                CacheErrorCodes.OPERATION_FAILED, msg="Redis 缓存发布补偿删除失败", cause=error
            ) from error
        if type(result) is not int or result not in (0, 1):
            raise CacheException(
                CacheErrorCodes.OPERATION_FAILED, msg="Redis 缓存发布补偿删除返回值无效"
            )
        return result

    @staticmethod
    async def _delete_chunk(client: Redis, chunk: list[str]) -> int:
        """一个 pipeline 内排入多条单键 DEL，并核对返回条数与取值。"""
        async with client.pipeline(transaction=False) as pipeline:
            for full_key in chunk:
                pipeline.delete(full_key)
            results = await pipeline.execute()
        if not isinstance(results, list) or len(results) != len(chunk):
            raise CacheException(
                CacheErrorCodes.OPERATION_FAILED, msg="Redis 删除 Pipeline 返回形状无效"
            )
        if any(type(result) is not int or result not in (0, 1) for result in results):
            raise CacheException(
                CacheErrorCodes.OPERATION_FAILED, msg="Redis 删除 Pipeline 返回值无效"
            )
        return sum(results)
