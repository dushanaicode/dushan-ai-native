import asyncio

from loguru import logger

from fixtures.cache_fixtures import requires_redis
from framework.starter_cache.core.cache_generation_coordinator import CacheGenerationCoordinator
from framework.starter_cache.core.cache_key_deleter import CacheKeyDeleter
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.definitions.enums.cache_generation_state_enum import (
    CacheGenerationStateEnum,
)
from framework.starter_cache.exception.cache_exception import CacheException

# 失效栅栏的收尾契约：begin 之后无论发生什么，generation 都必须回到 FINALIZED。
# 栅栏停在 ACTIVE 不会返回脏数据，但会让该前缀的回源发布一直被拒绝，读侧每次都判信封作废、
# 删键、加锁、回源，比没有缓存更慢且没有其他症状；这组用例锁住收尾行为及上一轮未收尾时的告警。
pytestmark = requires_redis


async def read_fence(cache, cache_key) -> str:
    """读取该前缀栅栏键的原始值 "<epoch>:<version>:<state>"。"""
    client = cache.get_client(cache_key)
    return await client.get(CacheGenerationCoordinator.build_generation_key(cache_key))


def fence_state(raw: str) -> str:
    """取出栅栏值里的状态段。"""
    return raw.rsplit(":", 1)[1]


async def test_failed_deletion_still_finalizes_the_fence(cache_case, monkeypatch):
    """删除失败时主异常照常上抛，但栅栏必须已经收尾，不能挡住后续回源。"""
    cache, keys, _ = cache_case
    await cache.set(keys.TestCacheKeys.ITEM, "kept", {"v": 1}, 60)

    async def failing_delete(self, client, full_keys):
        raise CacheException(CacheErrorCodes.OPERATION_FAILED, msg="注入的删除失败")

    monkeypatch.setattr(CacheKeyDeleter, "delete_keys", failing_delete)
    try:
        await cache.delete(keys.TestCacheKeys.ITEM, "kept")
    except CacheException as error:
        raised = error
    else:
        raised = None
    monkeypatch.undo()

    assert raised is not None and raised.msg == "注入的删除失败"
    assert fence_state(await read_fence(cache, keys.TestCacheKeys.ITEM)) == (
        CacheGenerationStateEnum.FINALIZED.code
    )
    # 栅栏已收尾，后续回源必须能重新写入缓存。
    assert await cache.get_or_load(keys.TestCacheKeys.ITEM, "after", _loader(7), 60) == 7
    assert (await cache.get(keys.TestCacheKeys.ITEM, "after")).value == 7


async def test_cancelled_invalidation_still_finalizes_the_fence(cache_case, monkeypatch):
    """调用方在删除期间取消时，取消照常传播，但栅栏要等到终态。"""
    cache, keys, _ = cache_case
    entered = asyncio.Event()

    async def blocking_delete(self, client, full_keys):
        entered.set()
        await asyncio.Event().wait()
        return 0

    monkeypatch.setattr(CacheKeyDeleter, "delete_keys", blocking_delete)
    task = asyncio.create_task(cache.delete(keys.TestCacheKeys.ITEM, "cancelled"))
    await entered.wait()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        cancelled = True
    else:
        cancelled = False
    monkeypatch.undo()

    assert cancelled and task.cancelled()
    assert fence_state(await read_fence(cache, keys.TestCacheKeys.ITEM)) == (
        CacheGenerationStateEnum.FINALIZED.code
    )


async def test_unfinalized_fence_blocks_caching_until_the_next_invalidation(cache_case):
    """栅栏停在 ACTIVE 时回源仍返回正确结果，但不写缓存；下一次成功失效后自愈。"""
    cache, keys, _ = cache_case
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    fence_key = CacheGenerationCoordinator.build_generation_key(keys.TestCacheKeys.ITEM)
    await cache.capture_generation(keys.TestCacheKeys.ITEM)
    epoch, version, _ = (await client.get(fence_key)).split(":")
    await client.set(fence_key, f"{epoch}:{version}:{CacheGenerationStateEnum.ACTIVE.code}")

    assert await cache.get_or_load(keys.TestCacheKeys.ITEM, "stuck", _loader("v"), 60) == "v"
    assert (await cache.get(keys.TestCacheKeys.ITEM, "stuck")).hit is False

    await cache.delete_all(keys.TestCacheKeys.ITEM)

    assert await cache.get_or_load(keys.TestCacheKeys.ITEM, "stuck", _loader("v"), 60) == "v"
    assert (await cache.get(keys.TestCacheKeys.ITEM, "stuck")).value == "v"


async def test_begin_warns_when_the_previous_round_never_finalized(cache_case):
    """上一轮没收尾是静默降级，必须在下一次失效时留下告警。"""
    cache, keys, _ = cache_case
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    fence_key = CacheGenerationCoordinator.build_generation_key(keys.TestCacheKeys.ITEM)
    await cache.capture_generation(keys.TestCacheKeys.ITEM)
    epoch, version, _ = (await client.get(fence_key)).split(":")
    await client.set(fence_key, f"{epoch}:{version}:{CacheGenerationStateEnum.ACTIVE.code}")

    messages: list[str] = []
    handler = logger.add(messages.append, level="WARNING", format="{message}")
    try:
        await cache.delete_all(keys.TestCacheKeys.ITEM)
    finally:
        logger.remove(handler)

    assert any(
        "缓存失效栅栏上一轮未收尾" in message and fence_key in message for message in messages
    )


async def test_healthy_invalidation_does_not_warn(cache_case):
    """正常失效不得产生告警，否则这条信号会被噪声淹没。"""
    cache, keys, _ = cache_case
    await cache.delete_all(keys.TestCacheKeys.ITEM)

    messages: list[str] = []
    handler = logger.add(messages.append, level="WARNING", format="{message}")
    try:
        await cache.delete_all(keys.TestCacheKeys.ITEM)
        await cache.delete(keys.TestCacheKeys.ITEM, "absent")
    finally:
        logger.remove(handler)

    assert not [message for message in messages if "缓存失效栅栏" in message]


def _loader(value):
    """返回固定值的回源函数。"""

    async def load():
        return value

    return load
