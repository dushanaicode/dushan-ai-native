from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from hashlib import sha256
from uuid import uuid4

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_cache.constants.cache_constants import CacheConstants
from framework.starter_cache.core.cache_generation_coordinator import CacheGenerationCoordinator
from framework.starter_cache.core.cache_key_deleter import CacheKeyDeleter
from framework.starter_cache.exception.cache_operation_exception import CacheOperationException
from framework.starter_cache.exception.cache_serialization_exception import (
    CacheSerializationException,
)
from framework.starter_cache.model.cache_generation_publication import CacheGenerationPublication
from framework.starter_cache.model.cache_generation_state import CacheGenerationState
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject

# 只有键为空，或者现有值属于同一个 generation 快照时才允许写入。
# 这样两个不同 generation 的回源结果不会互相覆盖，补偿删除也只会删掉自己那一份。
_PUBLISH_IF_GENERATION_MATCHES = """
-- cache_publish_if_generation_matches
local current = redis.call('GET', KEYS[1])
if current then
    if string.sub(current, 1, string.len(ARGV[2])) ~= ARGV[2] then
        return 0
    end
    local token_start = string.len(ARGV[2]) + 1
    local token_end = token_start + tonumber(ARGV[4]) - 1
    if string.sub(current, token_start, token_end) ~= ARGV[3] then
        return 0
    end
end
if tonumber(ARGV[5]) > 0 then
    redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[5])
else
    redis.call('SET', KEYS[1], ARGV[1])
end
return 1
"""


@framework
class CacheGenerationPublisher:
    """负责带 generation 快照的回源发布、读侧校验和失败补偿。

    发布分三步：CAS 写入带快照的信封 → 复查 generation 是否仍是当时那一代 →
    不是就删掉自己刚写的值并返回 False。补偿只按值精确匹配删除，
    因此不会误删其他请求写入的新值。

    直接写入（set_direct）不参与这个协议：调用方明确知道自己在覆盖，
    读侧遇到不带信封前缀的普通值会原样返回。
    """

    _coordinator: CacheGenerationCoordinator = Inject()
    _deleter: CacheKeyDeleter = Inject()

    @staticmethod
    async def set_direct(client: Redis, full_key: str, payload: bytes, ttl_seconds: int | None):
        """写入不参与 generation 协议的显式值。"""
        try:
            if ttl_seconds is None:
                result = await client.set(full_key, payload)
            else:
                result = await client.set(full_key, payload, ex=ttl_seconds)
        except RedisError as error:
            raise CacheOperationException(msg="Redis SET 操作失败", cause=error) from error
        if result is not True:
            raise CacheOperationException(msg="Redis SET 未返回成功")

    async def publish(
        self,
        client: Redis,
        full_key: str,
        payload: bytes,
        ttl_seconds: int | None,
        snapshot: tuple[CacheGenerationState, ...],
    ) -> bool:
        """发布一次回源结果；快照已过期时不写入或立即撤销，返回是否真正生效。"""
        if not self._coordinator.snapshot_allows_publication(snapshot):
            return False
        envelope = self.build_envelope(payload, snapshot)
        try:
            if not await self._write(client, full_key, envelope, snapshot, ttl_seconds):
                return False
            if await self._coordinator.snapshot_is_current(client, snapshot):
                return True
        except BaseException as error:
            await self.compensate(client, full_key, envelope, primary_error=error)
            raise
        await self.compensate(client, full_key, envelope)
        return False

    async def read(self, client: Redis, full_key: str) -> tuple[bool, str | None]:
        """读取并顺手清理 generation 已经作废的信封，返回 (是否命中, 载荷)。"""
        try:
            raw = await client.get(full_key)
        except RedisError as error:
            raise CacheOperationException(msg="Redis GET 操作失败", cause=error) from error
        if raw is None:
            return False, None
        is_current, payload = await self.decode_if_current(client, raw)
        if not is_current:
            await self.compensate(client, full_key, raw)
            return False, None
        return True, payload

    async def decode_if_current(self, client: Redis, raw: str) -> tuple[bool, str | None]:
        """解开信封；普通直接写入的值原样返回，作废的信封返回未命中。"""
        publication = self._parse(raw)
        if publication is None:
            return True, raw
        if not self._coordinator.snapshot_allows_publication(
            publication.generation_snapshot
        ) or not await self._coordinator.snapshot_is_current(
            client, publication.generation_snapshot
        ):
            return False, None
        try:
            return True, b64decode(publication.payload_base64, validate=True).decode("utf-8")
        except (BinasciiError, ValueError, UnicodeDecodeError) as error:
            raise CacheSerializationException(
                msg="缓存 generation 发布载荷无效", cause=error
            ) from error

    @classmethod
    def build_envelope(cls, payload: bytes, snapshot: tuple[CacheGenerationState, ...]) -> str:
        """构造带写入者身份与 generation 指纹的信封文本。"""
        publication = CacheGenerationPublication(
            owner_token=uuid4().hex,
            generation_token=cls.build_snapshot_token(snapshot),
            generation_snapshot=snapshot,
            payload_base64=b64encode(payload).decode("ascii"),
        )
        return (
            CacheConstants.GENERATION_PUBLICATION_PREFIX
            + publication.generation_token
            + CacheConstants.GENERATION_TOKEN_SEPARATOR
            + publication.model_dump_json()
        )

    @staticmethod
    def build_snapshot_token(snapshot: tuple[CacheGenerationState, ...]) -> str:
        """为快照生成稳定指纹，让 Lua 只比较定长前缀就能识别同代写入。"""
        payload = "\n".join(state.model_dump_json() for state in snapshot)
        return sha256(payload.encode("utf-8")).hexdigest()

    async def compensate(
        self,
        client: Redis,
        full_key: str,
        expected: str,
        *,
        primary_error: BaseException | None = None,
    ) -> None:
        """撤销自己写入的那一份值；调用方取消时也要等到删除得到终态。"""

        async def delete_owned_value() -> None:
            await self._deleter.delete_if_value_matches(client, full_key, expected)

        cleanup_error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
            delete_owned_value, "缓存回源发布补偿"
        )
        CleanupUtils.raise_collected_cleanup_errors(
            "缓存回源发布补偿失败",
            [] if cleanup_error is None else [cleanup_error],
            caller_cancellation=cancellation,
            primary_error=primary_error,
        )

    @classmethod
    async def _write(
        cls,
        client: Redis,
        full_key: str,
        envelope: str,
        snapshot: tuple[CacheGenerationState, ...],
        ttl_seconds: int | None,
    ) -> bool:
        """执行 CAS 写入，返回本次是否真正落盘。"""
        try:
            result = await client.eval(
                _PUBLISH_IF_GENERATION_MATCHES,
                1,
                full_key,
                envelope,
                CacheConstants.GENERATION_PUBLICATION_PREFIX,
                cls.build_snapshot_token(snapshot),
                CacheConstants.GENERATION_TOKEN_LENGTH,
                0 if ttl_seconds is None else ttl_seconds,
            )
        except RedisError as error:
            raise CacheOperationException(
                msg="Redis generation SET 操作失败", cause=error
            ) from error
        if type(result) is not int or result not in (0, 1):
            raise CacheOperationException(msg="Redis generation SET 返回值无效")
        return result == 1

    @classmethod
    def _parse(cls, raw: str) -> CacheGenerationPublication | None:
        """识别并校验信封；不是信封返回 None，是信封但结构不对则明确失败。"""
        if not raw.startswith(CacheConstants.GENERATION_PUBLICATION_PREFIX):
            return None
        encoded = raw.removeprefix(CacheConstants.GENERATION_PUBLICATION_PREFIX)
        token, separator, payload = encoded.partition(CacheConstants.GENERATION_TOKEN_SEPARATOR)
        try:
            publication = CacheGenerationPublication.model_validate_json(payload, strict=True)
        except (ValidationError, ValueError) as error:
            raise CacheSerializationException(
                msg="缓存 generation 发布信封无效", cause=error
            ) from error
        if (
            not separator
            or len(token) != CacheConstants.GENERATION_TOKEN_LENGTH
            or token != publication.generation_token
            or token != cls.build_snapshot_token(publication.generation_snapshot)
        ):
            raise CacheSerializationException(msg="缓存 generation 发布指纹无效")
        return publication
