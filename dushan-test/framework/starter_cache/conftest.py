import importlib
from uuid import uuid4

import pytest

from fixtures.cache_fixtures import (
    DAO_SOURCE,
    KEY_CONTAINER_SOURCE,
    REDIS_TARGET,
    CacheCase,
    app_values,
    clear_prefix,
    redis_values,
)
from fixtures.scanner_fixtures import module_package as module_package  # noqa: F401
from framework.starter_cache.core.cache_handler import CacheHandler


@pytest.fixture
def cache_prefix() -> str:
    """每个用例使用独立键前缀，避免共享实例上的用例互相干扰。"""
    return f"t{uuid4().hex[:16]}"


@pytest.fixture
def key_module(module_package, cache_prefix):  # noqa: F811
    """生成一个真实可扫描的模块，声明本用例使用的缓存键。"""
    package = f"cache_keys_{cache_prefix}"
    module_package(
        package,
        name=package,
        files={
            "keys.py": KEY_CONTAINER_SOURCE.format(prefix=cache_prefix),
            "dao.py": DAO_SOURCE.format(package=package),
        },
        scan_roots=(".",),
    )
    return importlib.import_module(f"{package}.keys")


@pytest.fixture
def module_values(key_module):
    """把测试模块接入模块声明，使容器经过真实扫描被发现。"""
    package = key_module.__name__.split(".")[0]
    return {"modules": {"packages": ["framework", package], "enabled": ["framework", package]}}


@pytest.fixture
async def cache_app(config_dir, module_values, key_module):
    """启动一个接入真实 Redis 的完整应用。"""
    from server.starter_server import create_app

    app = create_app(base_dir=config_dir(app_values(redis_values(), **module_values)), environ={})
    async with app.router.lifespan_context(app):
        yield app, key_module


@pytest.fixture
async def cache_case(cache_app):
    """进入应用执行边界后再解析组件，与真实请求/后台任务的解析约束一致。"""
    app, keys = cache_app
    context = app.state.application_context
    with context.execution():
        yield CacheCase(context.get_bean(CacheHandler), keys, app)


@pytest.fixture(autouse=True)
async def isolate_prefix(cache_prefix):
    """无论用例自己创建了几个应用，结束后都按前缀清理键、栅栏和锁。"""
    yield
    if REDIS_TARGET is None:
        return
    from redis.asyncio import Redis

    for client_settings in REDIS_TARGET["clients"]:
        client = Redis(
            host=REDIS_TARGET["host"],
            port=REDIS_TARGET["port"],
            username=REDIS_TARGET.get("username"),
            password=REDIS_TARGET.get("password"),
            db=client_settings["db"],
            decode_responses=True,
        )
        try:
            await clear_prefix(client, cache_prefix)
        finally:
            await client.aclose()
