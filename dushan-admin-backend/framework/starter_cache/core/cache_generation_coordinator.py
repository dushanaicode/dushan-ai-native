from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from framework.starter_cache.constants.cache_constants import CacheConstants
from framework.starter_cache.core.cache_generation_scripts import CacheGenerationScripts
from framework.starter_cache.core.cache_key_resolver import CacheKeyResolver
from framework.starter_cache.enums.cache_generation_state_enum import CacheGenerationStateEnum
from framework.starter_cache.exception.cache_operation_exception import CacheOperationException
from framework.starter_cache.model.cache_generation_state import CacheGenerationState
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_di.decorators.components import framework

_SEPARATOR = ":"
_LUA_SKIPPED = 0
_LUA_APPLIED = 1


@framework
class CacheGenerationCoordinator:
    """执行 generation 栅栏的状态机，解决「回源写入晚于失效」的经典竞态。

    读缓存未命中 → 回源查库 → 期间另一个请求改库并失效缓存 → 回源结果写入，
    如果没有栅栏，这份已经过期的值会一直留在缓存里。栅栏的做法是：回源前先记下
    前缀的 generation，写入时带上这份快照，写入后再确认 generation 没有变化，
    变化了就把自己刚写的值删掉。

    客户端由调用方按 CacheKey 解析后传入，本类不持有连接。
    """

    @staticmethod
    def build_generation_key(cache_key: CacheKey) -> str:
        """派生该前缀的栅栏键；栅栏键在独立命名空间，不会被业务前缀的失效删除。"""
        prefix = CacheKeyResolver.build_prefix(cache_key)
        return (
            f"{CacheConstants.GENERATION_KEY_PREFIX}:"
            f"{CacheConstants.GENERATION_PREFIX_SCOPE}:{prefix}"
        )

    async def capture_snapshot(
        self, client: Redis, cache_key: CacheKey
    ) -> tuple[CacheGenerationState, ...]:
        """回源开始前记录该前缀当前的栅栏状态。"""
        return (await self.read_state(client, self.build_generation_key(cache_key)),)

    @staticmethod
    def snapshot_allows_publication(snapshot: tuple[CacheGenerationState, ...]) -> bool:
        """快照里只要有一项仍在失效执行中，就不允许发布回源结果。"""
        return all(state.state is CacheGenerationStateEnum.FINALIZED for state in snapshot)

    async def snapshot_is_current(
        self, client: Redis, snapshot: tuple[CacheGenerationState, ...]
    ) -> bool:
        """确认快照记录的 epoch/version 仍然是当前值，且失效没有正在进行。"""
        current = tuple([await self.read_state(client, state.generation_key) for state in snapshot])
        return all(
            now.epoch == captured.epoch
            and now.version == captured.version
            and now.state is CacheGenerationStateEnum.FINALIZED
            for captured, now in zip(snapshot, current, strict=True)
        )

    async def read_state(self, client: Redis, generation_key: str) -> CacheGenerationState:
        """读取栅栏状态；键不存在时原子初始化，保证并发读拿到同一个 epoch。"""
        try:
            payload = await client.eval(
                CacheGenerationScripts.READ_OR_INITIALIZE,
                1,
                generation_key,
                uuid4().hex,
                CacheGenerationStateEnum.FINALIZED.code,
            )
        except RedisError as error:
            raise CacheOperationException(msg="读取缓存 generation 失败", cause=error) from error
        return self._parse(generation_key, payload)

    async def begin(self, client: Redis, generation_key: str) -> CacheGenerationState:
        """开始一轮失效：版本自增并进入 ACTIVE，期间拒绝任何回源发布。"""
        try:
            payload = await client.eval(
                CacheGenerationScripts.BEGIN,
                1,
                generation_key,
                CacheGenerationStateEnum.ACTIVE.code,
                CacheGenerationStateEnum.FINALIZED.code,
                uuid4().hex,
            )
        except RedisError as error:
            raise CacheOperationException(
                msg="开始缓存失效 generation 失败", cause=error
            ) from error
        generation = self._parse(generation_key, payload)
        if (
            generation.version <= CacheConstants.INITIAL_GENERATION_VERSION
            or generation.state is not CacheGenerationStateEnum.ACTIVE
        ):
            raise CacheOperationException(msg="缓存失效 generation 返回值无效")
        return generation

    async def finalize(self, client: Redis, generation: CacheGenerationState) -> None:
        """结束本轮失效；已经被更新一轮覆盖时安静跳过，版本回退则明确失败。"""
        try:
            result = await client.eval(
                CacheGenerationScripts.FINALIZE,
                1,
                generation.generation_key,
                generation.epoch,
                generation.version,
                CacheGenerationStateEnum.ACTIVE.code,
                CacheGenerationStateEnum.FINALIZED.code,
            )
        except RedisError as error:
            raise CacheOperationException(
                msg="完成缓存失效 generation 失败", cause=error
            ) from error
        if type(result) is not int or result not in (_LUA_SKIPPED, _LUA_APPLIED):
            raise CacheOperationException(msg="缓存失效 generation 完成返回值无效")

    @staticmethod
    def _parse(generation_key: str, payload: object) -> CacheGenerationState:
        """解析 "<epoch>:<version>:<state>"，任何形状异常都当作协议错误。"""
        if isinstance(payload, bytes):
            try:
                value = payload.decode("utf-8")
            except UnicodeDecodeError as error:
                raise CacheOperationException(
                    msg="缓存 generation 编码无效", cause=error
                ) from error
        elif isinstance(payload, str):
            value = payload
        else:
            raise CacheOperationException(msg="缓存 generation 类型无效")

        epoch, first, remainder = value.partition(_SEPARATOR)
        version_text, second, state_code = remainder.partition(_SEPARATOR)
        if not first or not second or not epoch:
            raise CacheOperationException(msg="缓存 generation 状态无效")
        try:
            version = int(version_text)
        except ValueError as error:
            raise CacheOperationException(msg="缓存 generation 版本无效", cause=error) from error
        state = CacheGenerationStateEnum.get_by_code(state_code)
        if version < CacheConstants.INITIAL_GENERATION_VERSION or state is None:
            raise CacheOperationException(msg="缓存 generation 状态无效")
        return CacheGenerationState(
            generation_key=generation_key, epoch=epoch, version=version, state=state
        )
