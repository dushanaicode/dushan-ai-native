import asyncio

import pytest

from fixtures.cache_fixtures import app_values, redis_values, requires_redis
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.exception.cache_serialization_exception import (
    CacheSerializationException,
)
from server.starter_server import create_app

pytestmark = requires_redis


def counting_loader(value, calls: list, event: asyncio.Event | None = None):
    """记录回源次数的加载器，可选地等待外部事件以便制造竞态。"""

    async def load():
        calls.append(value)
        if event is not None:
            await event.wait()
        return value

    return load


async def test_load_through_caches_the_loaded_value_and_skips_the_second_load(cache_case):
    cache, keys, _ = cache_case
    calls = []

    first = await cache.get_or_load(keys.TestCacheKeys.ITEM, "u1", counting_loader(7, calls), 60)
    second = await cache.get_or_load(keys.TestCacheKeys.ITEM, "u1", counting_loader(9, calls), 60)

    assert first == 7 and second == 7 and calls == [7]


async def test_concurrent_load_through_on_one_key_loads_only_once(cache_case):
    cache, keys, _ = cache_case
    calls = []
    gate = asyncio.Event()
    tasks = [
        asyncio.create_task(
            cache.get_or_load(keys.TestCacheKeys.ITEM, "hot", counting_loader(5, calls, gate), 60)
        )
        for _ in range(20)
    ]
    await asyncio.sleep(0.1)
    gate.set()

    assert await asyncio.gather(*tasks) == [5] * 20
    assert calls == [5]


async def test_null_result_is_cached_with_the_null_value_ttl(cache_case):
    cache, keys, _ = cache_case
    calls = []
    client = cache.get_client(keys.TestCacheKeys.ITEM)

    assert (
        await cache.get_or_load(keys.TestCacheKeys.ITEM, "none", counting_loader(None, calls))
        is None
    )
    ttl = await client.ttl(cache.build_full_key(keys.TestCacheKeys.ITEM, "none"))

    assert 0 < ttl <= 60
    assert (await cache.get(keys.TestCacheKeys.ITEM, "none")).hit is True
    assert (
        await cache.get_or_load(keys.TestCacheKeys.ITEM, "none", counting_loader(None, calls))
        is None
    )
    assert calls == [None]


async def test_null_result_is_not_cached_when_protection_is_disabled(
    config_dir, module_values, key_module
):
    app = create_app(
        base_dir=config_dir(app_values(redis_values(null_value_enabled=False), **module_values)),
        environ={},
    )
    calls = []
    async with app.router.lifespan_context(app):
        context = app.state.application_context
        with context.execution():
            cache = context.get_bean(CacheHandler)
            for _ in range(2):
                assert (
                    await cache.get_or_load(
                        key_module.TestCacheKeys.ITEM, "gap", counting_loader(None, calls)
                    )
                    is None
                )
            assert (await cache.get(key_module.TestCacheKeys.ITEM, "gap")).hit is False
            await cache.delete_all(key_module.TestCacheKeys.ITEM)
    assert calls == [None, None]


async def test_invalidation_during_load_prevents_publishing_the_stale_value(cache_case):
    cache, keys, _ = cache_case
    calls = []
    gate = asyncio.Event()
    loading = asyncio.create_task(
        cache.get_or_load(keys.TestCacheKeys.ITEM, "race", counting_loader("old", calls, gate), 60)
    )
    await asyncio.sleep(0.1)

    # 回源还没返回时发生一次整段失效，这份结果在写入后必须被自己撤销。
    await cache.delete_all(keys.TestCacheKeys.ITEM)
    gate.set()

    assert await loading == "old"
    assert (await cache.get(keys.TestCacheKeys.ITEM, "race")).hit is False


async def test_delete_during_load_leaves_no_key_behind(cache_case):
    cache, keys, _ = cache_case
    calls = []
    gate = asyncio.Event()
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    loading = asyncio.create_task(
        cache.get_or_load(keys.TestCacheKeys.ITEM, "solo", counting_loader("v", calls, gate), 60)
    )
    await asyncio.sleep(0.1)
    await cache.delete(keys.TestCacheKeys.ITEM, "solo")
    gate.set()
    await loading

    assert await client.exists(cache.build_full_key(keys.TestCacheKeys.ITEM, "solo")) == 0


async def test_corrupted_entry_is_dropped_and_reloaded(cache_case):
    cache, keys, _ = cache_case
    calls = []
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    await client.set(cache.build_full_key(keys.TestCacheKeys.ITEM, "bad"), "{broken")

    assert (
        await cache.get_or_load(keys.TestCacheKeys.ITEM, "bad", counting_loader(3, calls), 60) == 3
    )
    assert calls == [3]
    assert (await cache.get(keys.TestCacheKeys.ITEM, "bad")).value == 3


async def test_cancelling_the_caller_releases_the_distributed_lock(cache_case):
    cache, keys, _ = cache_case
    calls = []
    gate = asyncio.Event()
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    full_key = cache.build_full_key(keys.TestCacheKeys.ITEM, "cancel")
    lock_key = f"lock:cache_lock:default:{full_key}"

    loading = asyncio.create_task(
        cache.get_or_load(keys.TestCacheKeys.ITEM, "cancel", counting_loader("v", calls, gate), 60)
    )
    await asyncio.sleep(0.15)
    assert await client.exists(lock_key) == 1

    loading.cancel()
    with pytest.raises(asyncio.CancelledError):
        await loading
    await asyncio.sleep(0.1)

    assert await client.exists(lock_key) == 0
    assert await client.exists(full_key) == 0


async def test_two_applications_share_one_redis_lock_for_the_same_key(
    config_dir, module_values, key_module
):
    apps = [
        create_app(base_dir=config_dir(app_values(redis_values(), **module_values)), environ={})
        for _ in range(2)
    ]
    calls = []
    gate = asyncio.Event()
    async with apps[0].router.lifespan_context(apps[0]):
        async with apps[1].router.lifespan_context(apps[1]):
            handlers = []
            for app in apps:
                with app.state.application_context.execution():
                    handlers.append(app.state.application_context.get_bean(CacheHandler))
            assert handlers[0] is not handlers[1]

            async def load_from(index):
                with apps[index].state.application_context.execution():
                    return await handlers[index].get_or_load(
                        key_module.TestCacheKeys.ITEM,
                        "shared",
                        counting_loader(index, calls, gate),
                        60,
                        wait_seconds=5.0,
                    )

            first = asyncio.create_task(load_from(0))
            await asyncio.sleep(0.2)
            second = asyncio.create_task(load_from(1))
            await asyncio.sleep(0.2)
            gate.set()
            results = await asyncio.gather(first, second)

            # 第二个应用等到锁后先重读缓存，命中后不再回源。
            assert len(calls) == 1
            assert results[0] == results[1] == calls[0]
            with apps[0].state.application_context.execution():
                await handlers[0].delete_all(key_module.TestCacheKeys.ITEM)


async def test_serialization_failure_inside_load_is_not_silently_swallowed(cache_case):
    cache, keys, _ = cache_case

    async def load():
        return object()

    with pytest.raises(CacheSerializationException):
        await cache.get_or_load(keys.TestCacheKeys.ITEM, "unserializable", load, 60)


async def test_manual_capture_then_publish_writes_when_generation_is_unchanged(cache_case):
    """手动控制时序：先取快照，自己取数，再发布；期间没有失效则正常写入。"""
    cache, keys, _ = cache_case

    snapshot = await cache.capture_generation(keys.TestCacheKeys.ITEM)
    assert await cache.publish_loaded_value(
        keys.TestCacheKeys.ITEM, "manual", {"token": "abc"}, snapshot, 120
    )

    result = await cache.get(keys.TestCacheKeys.ITEM, "manual")
    assert result.hit is True and result.value == {"token": "abc"}
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    assert 0 < await client.ttl(cache.build_full_key(keys.TestCacheKeys.ITEM, "manual")) <= 120


async def test_manual_publish_is_refused_after_an_invalidation(cache_case):
    """取快照之后发生失效，这份结果必须发布失败且不留残留。"""
    cache, keys, _ = cache_case

    snapshot = await cache.capture_generation(keys.TestCacheKeys.ITEM)
    await cache.delete_all(keys.TestCacheKeys.ITEM)

    assert not await cache.publish_loaded_value(
        keys.TestCacheKeys.ITEM, "stale", {"token": "old"}, snapshot, 120
    )
    assert (await cache.get(keys.TestCacheKeys.ITEM, "stale")).hit is False


async def test_manual_publish_skips_null_when_protection_is_disabled(
    config_dir, module_values, key_module
):
    """空值防穿透关闭时，手动发布同样不写入空值，并如实返回 False。"""
    app = create_app(
        base_dir=config_dir(app_values(redis_values(null_value_enabled=False), **module_values)),
        environ={},
    )
    async with app.router.lifespan_context(app):
        context = app.state.application_context
        with context.execution():
            cache = context.get_bean(CacheHandler)
            snapshot = await cache.capture_generation(key_module.TestCacheKeys.ITEM)
            assert not await cache.publish_loaded_value(
                key_module.TestCacheKeys.ITEM, "none", None, snapshot
            )
            assert (await cache.get(key_module.TestCacheKeys.ITEM, "none")).hit is False
