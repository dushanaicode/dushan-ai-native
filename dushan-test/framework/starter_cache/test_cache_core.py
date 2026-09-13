import asyncio

import pytest
from pydantic import BaseModel

from fixtures.cache_fixtures import requires_redis
from framework.starter_cache.exception.cache_config_exception import CacheConfigException
from framework.starter_cache.exception.cache_operation_exception import CacheOperationException
from framework.starter_cache.exception.cache_serialization_exception import (
    CacheSerializationException,
)

pytestmark = requires_redis


class SampleModel(BaseModel):
    """用于验证 Pydantic 模型在缓存往返后的形态。"""

    name: str
    score: int


async def test_set_and_get_round_trip_keeps_value_and_reports_hit(cache_case):
    cache, keys, _ = cache_case
    await cache.set(keys.TestCacheKeys.ITEM, "a", {"name": "渡山", "score": 7})

    result = await cache.get(keys.TestCacheKeys.ITEM, "a")
    assert result.hit is True
    assert result.value == {"name": "渡山", "score": 7}


async def test_missing_key_reports_miss_without_value(cache_case):
    cache, keys, _ = cache_case
    result = await cache.get(keys.TestCacheKeys.ITEM, "absent")
    assert result.hit is False and result.value is None


async def test_cached_null_is_a_hit_not_a_miss(cache_case):
    cache, keys, _ = cache_case
    await cache.set(keys.TestCacheKeys.ITEM, "empty", None)

    result = await cache.get(keys.TestCacheKeys.ITEM, "empty")
    assert result.hit is True and result.value is None


async def test_pydantic_model_and_set_are_serialized_as_json(cache_case):
    cache, keys, _ = cache_case
    await cache.set(keys.TestCacheKeys.ITEM, "model", SampleModel(name="渡山", score=3))
    await cache.set(keys.TestCacheKeys.ITEM, "set", {"b", "a"})

    assert (await cache.get(keys.TestCacheKeys.ITEM, "model")).value == {"name": "渡山", "score": 3}
    assert (await cache.get(keys.TestCacheKeys.ITEM, "set")).value == ["a", "b"]


@pytest.mark.parametrize("value", [object(), {1, 2, object()}, float("nan")])
async def test_unsupported_values_fail_before_writing(cache_case, value):
    cache, keys, _ = cache_case
    with pytest.raises(CacheSerializationException):
        await cache.set(keys.TestCacheKeys.ITEM, "bad", value)
    assert (await cache.get(keys.TestCacheKeys.ITEM, "bad")).hit is False


async def test_corrupted_payload_raises_instead_of_returning_raw_text(cache_case):
    cache, keys, _ = cache_case
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    await client.set(cache.build_full_key(keys.TestCacheKeys.ITEM, "broken"), "{not-json")

    with pytest.raises(CacheSerializationException):
        await cache.get(keys.TestCacheKeys.ITEM, "broken")


async def test_explicit_ttl_is_applied_and_key_expires(cache_case):
    cache, keys, _ = cache_case
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    await cache.set(keys.TestCacheKeys.ITEM, "ttl", "v", ttl_seconds=1)

    assert 0 < await client.ttl(cache.build_full_key(keys.TestCacheKeys.ITEM, "ttl")) <= 1
    await asyncio.sleep(1.2)
    assert (await cache.get(keys.TestCacheKeys.ITEM, "ttl")).hit is False


async def test_cache_key_default_ttl_applies_when_call_does_not_pass_one(cache_case):
    cache, keys, _ = cache_case
    client = cache.get_client(keys.TestCacheKeys.SHORT)
    await cache.set(keys.TestCacheKeys.SHORT, "auto", "v")

    assert 0 < await client.ttl(cache.build_full_key(keys.TestCacheKeys.SHORT, "auto")) <= 1


async def test_key_without_default_ttl_is_written_without_expiry(cache_case):
    cache, keys, _ = cache_case
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    await cache.set(keys.TestCacheKeys.ITEM, "forever", "v")

    assert await client.ttl(cache.build_full_key(keys.TestCacheKeys.ITEM, "forever")) == -1


@pytest.mark.parametrize("ttl", [0, -1, 2592001])
async def test_invalid_ttl_is_rejected_before_writing(cache_case, ttl):
    cache, keys, _ = cache_case
    with pytest.raises(CacheConfigException):
        await cache.set(keys.TestCacheKeys.ITEM, "ttl-bad", "v", ttl_seconds=ttl)
    assert (await cache.get(keys.TestCacheKeys.ITEM, "ttl-bad")).hit is False


async def test_delete_removes_one_key_and_reports_count(cache_case):
    cache, keys, _ = cache_case
    await cache.set(keys.TestCacheKeys.ITEM, "one", 1)

    assert await cache.delete(keys.TestCacheKeys.ITEM, "one") == 1
    assert await cache.delete(keys.TestCacheKeys.ITEM, "one") == 0
    assert (await cache.get(keys.TestCacheKeys.ITEM, "one")).hit is False


async def test_delete_many_removes_only_listed_identifiers(cache_case):
    cache, keys, _ = cache_case
    for index in range(5):
        await cache.set(keys.TestCacheKeys.ITEM, f"k{index}", index)

    assert await cache.delete_many(keys.TestCacheKeys.ITEM, ["k0", "k1", "missing"]) == 2
    assert (await cache.get(keys.TestCacheKeys.ITEM, "k2")).hit is True
    assert await cache.delete_many(keys.TestCacheKeys.ITEM, []) == 0


async def test_delete_all_clears_the_prefix_across_chunk_boundary(cache_case):
    cache, keys, _ = cache_case
    total = 1200
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    async with client.pipeline(transaction=False) as pipeline:
        for index in range(total):
            pipeline.set(cache.build_full_key(keys.TestCacheKeys.ITEM, f"bulk{index}"), '"v"')
        await pipeline.execute()
    await cache.set(keys.TestCacheKeys.SHORT, "other", "keep", ttl_seconds=60)

    assert await cache.delete_all(keys.TestCacheKeys.ITEM) == total
    assert (await cache.get(keys.TestCacheKeys.SHORT, "other")).hit is True


async def test_get_and_delete_consumes_the_value_exactly_once(cache_case):
    cache, keys, _ = cache_case
    await cache.set(keys.TestCacheKeys.ITEM, "once", "ticket")

    first = await cache.get_and_delete(keys.TestCacheKeys.ITEM, "once")
    second = await cache.get_and_delete(keys.TestCacheKeys.ITEM, "once")
    assert first.hit is True and first.value == "ticket"
    assert second.hit is False


async def test_clients_are_isolated_by_declared_client_name(cache_case):
    cache, keys, _ = cache_case
    await cache.set(keys.TestCacheKeys.ITEM, "x", "default-db")
    await cache.set(keys.TestCacheKeys.SECOND, "x", "second-db")

    assert cache.get_client(keys.TestCacheKeys.ITEM) is not cache.get_client(
        keys.TestCacheKeys.SECOND
    )
    assert (await cache.get(keys.TestCacheKeys.ITEM, "x")).value == "default-db"
    assert (await cache.get(keys.TestCacheKeys.SECOND, "x")).value == "second-db"


@pytest.mark.parametrize("identifier", ["", " ", "a b", "a\n", "a*", "a?", "a[1]"])
async def test_unsafe_identifiers_are_rejected(cache_case, identifier):
    cache, keys, _ = cache_case
    with pytest.raises(CacheConfigException):
        await cache.set(keys.TestCacheKeys.ITEM, identifier, "v")


async def test_eval_atomic_runs_a_multi_key_script_on_the_declared_client(cache_case):
    """内部 Lua 入口：多键脚本在该 CacheKey 所属客户端上原子执行。"""
    cache, keys, _ = cache_case
    script = "redis.call('SET', KEYS[1], ARGV[1]); redis.call('SET', KEYS[2], ARGV[2]); return 2"

    assert await cache.eval_atomic(keys.TestCacheKeys.ITEM, ("a", "b"), script, ("1", "2")) == 2

    client = cache.get_client(keys.TestCacheKeys.ITEM)
    assert await client.get(cache.build_full_key(keys.TestCacheKeys.ITEM, "a")) == "1"
    assert await client.get(cache.build_full_key(keys.TestCacheKeys.ITEM, "b")) == "2"


async def test_eval_atomic_keys_carry_the_cache_key_prefix(cache_case):
    """脚本拿到的是带前缀的物理键，调用方无法绕开键声明写到别处。"""
    cache, keys, _ = cache_case

    received = await cache.eval_atomic(keys.TestCacheKeys.ITEM, ("only",), "return KEYS[1]")

    assert received == cache.build_full_key(keys.TestCacheKeys.ITEM, "only")
    assert received.startswith(f"{keys.TestCacheKeys.ITEM.key}:")


async def test_eval_atomic_accepts_a_script_without_keys(cache_case):
    """无键脚本合法，KEYS 数量按传入标识计算。"""
    cache, keys, _ = cache_case
    assert await cache.eval_atomic(keys.TestCacheKeys.ITEM, (), "return #KEYS") == 0


@pytest.mark.parametrize("identifier", ["", "a b", "a*"])
async def test_eval_atomic_rejects_unsafe_identifiers(cache_case, identifier):
    """标识仍走统一校验，不因为是内部脚本入口就放宽。"""
    cache, keys, _ = cache_case
    with pytest.raises(CacheConfigException):
        await cache.eval_atomic(keys.TestCacheKeys.ITEM, (identifier,), "return 1")


async def test_eval_atomic_reports_script_failure_as_cache_operation_error(cache_case):
    """脚本报错按缓存操作失败上报，并保留原始 Redis 异常。"""
    cache, keys, _ = cache_case

    with pytest.raises(CacheOperationException) as failure:
        await cache.eval_atomic(keys.TestCacheKeys.ITEM, ("x",), "this is not lua")
    assert failure.value.__cause__ is not None
