import importlib

import pytest

from fixtures.cache_fixtures import requires_redis
from framework.starter_cache.repository.base_cache_dao import BaseCacheDAO

pytestmark = requires_redis


@pytest.fixture
def item_dao(cache_case):
    """从真实容器取出经过扫描装配的 DAO 子类实例。"""
    _, keys, app = cache_case
    package = keys.__name__.split(".")[0]
    dao_type = importlib.import_module(f"{package}.dao").ItemCacheDAO
    return app.state.application_context.get_bean(dao_type), keys


def test_base_class_is_not_a_di_component_itself(item_dao):
    """基类的构造参数是业务 CacheKey，容器不应该也无法解析它。"""
    from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata

    assert DiComponentMetadata.ATTRIBUTE not in vars(BaseCacheDAO)


def test_subclass_receives_the_handler_through_the_inherited_inject_field(item_dao):
    """基类上声明的 Inject 字段在子类实例上由容器解析，不需要子类重复声明。"""
    dao, keys = item_dao

    assert isinstance(dao, BaseCacheDAO)
    assert dao.cache_key is keys.TestCacheKeys.ITEM
    assert dao.get_client() is not None


async def test_dao_round_trip_delegates_to_the_bound_cache_key(item_dao):
    dao, keys = item_dao
    await dao.set("u1", {"name": "渡山"})

    result = await dao.get("u1")
    assert result.hit is True and result.value == {"name": "渡山"}
    assert dao.build_full_key("u1") == f"{keys.TestCacheKeys.ITEM.key}:u1"


async def test_dao_reports_miss_and_cached_null_separately(item_dao):
    dao, _ = item_dao
    await dao.set("empty", None)

    assert (await dao.get("absent")).hit is False
    cached = await dao.get("empty")
    assert cached.hit is True and cached.value is None


async def test_dao_delete_paths_cover_single_batch_and_prefix(item_dao):
    dao, _ = item_dao
    for index in range(4):
        await dao.set(f"k{index}", index)

    assert await dao.delete("k0") == 1
    assert await dao.delete_many(["k1", "missing"]) == 1
    assert await dao.delete_many([]) == 0
    assert await dao.delete_all() == 2
    assert (await dao.get("k3")).hit is False


async def test_dao_get_and_delete_consumes_once(item_dao):
    dao, _ = item_dao
    await dao.set("ticket", "once")

    assert (await dao.get_and_delete("ticket")).value == "once"
    assert (await dao.get_and_delete("ticket")).hit is False


async def test_dao_get_or_load_falls_back_to_the_loader_only_once(item_dao):
    dao, _ = item_dao
    calls = []

    async def loader():
        calls.append(1)
        return {"loaded": True}

    assert await dao.get_or_load("lazy", loader, 60) == {"loaded": True}
    assert await dao.get_or_load("lazy", loader, 60) == {"loaded": True}
    assert calls == [1]


async def test_dao_ttl_comes_from_the_bound_cache_key_and_can_be_overridden(item_dao):
    dao, _ = item_dao
    client = dao.get_client()

    await dao.set("forever", 1)
    assert await client.ttl(dao.build_full_key("forever")) == -1

    await dao.set("short", 1, ttl_seconds=60)
    assert 0 < await client.ttl(dao.build_full_key("short")) <= 60


async def test_two_applications_get_independent_dao_instances(
    config_dir, module_values, key_module
):
    """DAO 是容器管理的单例，不同应用各有一份，不跨应用共享 handler。"""
    from fixtures.cache_fixtures import app_values, redis_values
    from server.starter_server import create_app

    package = key_module.__name__.split(".")[0]
    dao_type = importlib.import_module(f"{package}.dao").ItemCacheDAO
    instances, clients = [], []
    first = create_app(base_dir=config_dir(app_values(redis_values(), **module_values)), environ={})
    second = create_app(
        base_dir=config_dir(app_values(redis_values(), **module_values)), environ={}
    )
    async with first.router.lifespan_context(first):
        async with second.router.lifespan_context(second):
            for app in (first, second):
                # Inject 字段按所属容器解析，因此取客户端必须在各自的执行边界内进行。
                with app.state.application_context.execution():
                    instance = app.state.application_context.get_bean(dao_type)
                    instances.append(instance)
                    clients.append(instance.get_client())
            assert instances[0] is not instances[1]
            assert clients[0] is not clients[1]
