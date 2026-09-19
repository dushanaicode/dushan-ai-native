import pytest
from pydantic import BaseModel

from fixtures.cache_fixtures import app_values, redis_values, requires_redis
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.decorators.cache_evict import invalidate
from framework.starter_cache.decorators.cacheable import cache
from framework.starter_cache.exception.cache_exception import CacheException
from server.starter_server import create_app

pytestmark = requires_redis


class Role(BaseModel):
    """被缓存函数的声明返回类型。"""

    id: int
    name: str


async def test_cache_decorator_serves_the_second_call_from_redis(cache_case):
    cache_handler, keys, _ = cache_case
    calls = []

    @cache(keys.TestCacheKeys.ITEM, key="id:{{role_id}}", ttl_seconds=60)
    async def load_role(role_id: int) -> Role:
        calls.append(role_id)
        return Role(id=role_id, name="管理员")

    assert await load_role(1) == Role(id=1, name="管理员")
    second = await load_role(1)

    assert second == Role(id=1, name="管理员") and isinstance(second, Role)
    assert calls == [1]
    assert (await cache_handler.get(keys.TestCacheKeys.ITEM, "id:1")).value == {
        "id": 1,
        "name": "管理员",
    }


async def test_cache_decorator_without_template_builds_a_key_from_arguments(cache_case):
    _, keys, _ = cache_case
    calls = []

    @cache(keys.TestCacheKeys.ITEM, ttl_seconds=60)
    async def sum_values(left: int, right: int) -> int:
        calls.append((left, right))
        return left + right

    assert await sum_values(1, 2) == 3
    assert await sum_values(1, 2) == 3
    assert await sum_values(2, 1) == 3
    assert calls == [(1, 2), (2, 1)]


async def test_cache_decorator_respects_unless(cache_case):
    _, keys, _ = cache_case
    calls = []

    @cache(
        keys.TestCacheKeys.ITEM,
        key="u:{{value}}",
        ttl_seconds=60,
        unless=lambda result, *_: result is None,
    )
    async def maybe(value: int) -> int | None:
        calls.append(value)
        return None if value == 0 else value

    assert await maybe(0) is None and await maybe(0) is None
    assert await maybe(5) == 5 and await maybe(5) == 5
    assert calls == [0, 0, 5]


async def test_invalidate_decorator_removes_one_entry_after_the_method_succeeds(cache_case):
    cache_handler, keys, _ = cache_case
    await cache_handler.set(keys.TestCacheKeys.ITEM, "id:3", {"id": 3, "name": "旧"})

    @invalidate(keys.TestCacheKeys.ITEM, key="id:{{role_id}}")
    async def update_role(role_id: int) -> str:
        return "done"

    assert await update_role(3) == "done"
    assert (await cache_handler.get(keys.TestCacheKeys.ITEM, "id:3")).hit is False


async def test_invalidate_decorator_can_clear_the_whole_prefix(cache_case):
    cache_handler, keys, _ = cache_case
    for index in range(3):
        await cache_handler.set(keys.TestCacheKeys.ITEM, f"id:{index}", index)

    @invalidate(keys.TestCacheKeys.ITEM, all_entries=True)
    async def rebuild() -> None:
        return None

    await rebuild()
    for index in range(3):
        assert (await cache_handler.get(keys.TestCacheKeys.ITEM, f"id:{index}")).hit is False


async def test_invalidate_is_skipped_when_the_method_raises(cache_case):
    cache_handler, keys, _ = cache_case
    await cache_handler.set(keys.TestCacheKeys.ITEM, "id:9", 9)

    @invalidate(keys.TestCacheKeys.ITEM, key="id:{{role_id}}")
    async def failing(role_id: int) -> None:
        raise RuntimeError("业务失败")

    with pytest.raises(RuntimeError):
        await failing(9)
    assert (await cache_handler.get(keys.TestCacheKeys.ITEM, "id:9")).hit is True


async def test_decorator_resolves_components_from_the_current_application(
    config_dir, module_values, key_module
):
    calls = []

    @cache(key_module.TestCacheKeys.ITEM, key="app:{{value}}", ttl_seconds=60)
    async def load(value: int) -> int:
        calls.append(value)
        return value

    # 第一个应用用完即关闭；装饰器如果把组件缓存在类上，第二个应用会拿到已销毁的实例。
    for round_index in range(2):
        app = create_app(
            base_dir=config_dir(app_values(redis_values(), **module_values)), environ={}
        )
        async with app.router.lifespan_context(app):
            context = app.state.application_context
            with context.execution():
                assert await load(round_index) == round_index
                assert context.get_bean(CacheHandler) is not None
                await context.get_bean(CacheHandler).delete_all(key_module.TestCacheKeys.ITEM)
    assert calls == [0, 1]


def test_cache_decorator_requires_a_resolvable_return_type(key_module):
    with pytest.raises(CacheException, match="可解析的返回类型"):

        @cache(key_module.TestCacheKeys.ITEM, ttl_seconds=60)
        async def missing_annotation(value):
            return value


def test_cache_decorator_rejects_unknown_template_parameters(key_module):
    with pytest.raises(CacheException, match="未知参数"):

        @cache(key_module.TestCacheKeys.ITEM, key="{{absent}}", ttl_seconds=60)
        async def load(value: int) -> int:
            return value


def test_cache_decorator_rejects_invalid_ttl(key_module):
    with pytest.raises(CacheException, match="正整数秒"):
        cache(key_module.TestCacheKeys.ITEM, ttl_seconds=0)


def test_invalidate_requires_exactly_one_target(key_module):
    with pytest.raises(CacheException, match="只能指定"):
        invalidate(key_module.TestCacheKeys.ITEM)
    with pytest.raises(CacheException, match="只能指定"):
        invalidate(key_module.TestCacheKeys.ITEM, key="a", all_entries=True)


def test_decorators_require_a_cache_key_object(key_module):
    with pytest.raises(CacheException, match="必须传入 CacheKey"):
        cache("plain-prefix")
    with pytest.raises(CacheException, match="必须传入 CacheKey"):
        invalidate("plain-prefix", all_entries=True)
