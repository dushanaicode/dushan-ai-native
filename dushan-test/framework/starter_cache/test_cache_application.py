import asyncio

import httpx
import pytest
from fastapi import Depends

from fixtures.cache_fixtures import app_values, redis_values, requires_redis
from fixtures.public_web_app import create_public_app
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.exception.cache_connection_exception import CacheConnectionException
from framework.starter_di.context.get_bean import get_bean
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_di.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.exception.di_exception import DiException

pytestmark = requires_redis


def build_app(config_dir, module_values, **overrides):
    return create_public_app(
        base_dir=config_dir(app_values(redis_values(**overrides), **module_values)), environ={}
    )


async def test_http_request_and_background_task_share_the_application_cache(
    config_dir, module_values, key_module, cache_prefix
):
    app = build_app(config_dir, module_values)
    item = key_module.TestCacheKeys.ITEM

    @app.post("/cache/{identifier}")
    async def write(identifier: str, cache=Depends(DiDependency(CacheHandler))):
        await cache.set(item, identifier, {"from": "http"})
        return {"written": identifier}

    @app.get("/cache/{identifier}")
    async def read(identifier: str, cache=Depends(DiDependency(CacheHandler))):
        result = await cache.get(item, identifier)
        return {"hit": result.hit, "value": result.value}

    async with app.router.lifespan_context(app):
        context = app.state.application_context
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            assert (await client.post("/cache/k1")).json() == {"written": "k1"}
            assert (await client.get("/cache/k1")).json() == {
                "hit": True,
                "value": {"from": "http"},
            }

        async def from_task():
            return await get_bean(CacheHandler).get(item, "k1")

        assert (await context.tasks.run(from_task)).value == {"from": "http"}
        with context.execution():
            await context.get_bean(CacheHandler).delete_all(item)


async def test_each_application_owns_its_own_manager_and_connections(
    config_dir, module_values, key_module, cache_prefix
):
    first, second = build_app(config_dir, module_values), build_app(config_dir, module_values)
    async with first.router.lifespan_context(first):
        async with second.router.lifespan_context(second):
            managers = []
            handlers = []
            for app in (first, second):
                with app.state.application_context.execution():
                    managers.append(app.state.application_context.get_bean(CacheManager))
                    handlers.append(app.state.application_context.get_bean(CacheHandler))

            assert managers[0] is not managers[1]
            assert handlers[0] is not handlers[1]
            assert managers[0].get_client("default") is not managers[1].get_client("default")
            assert first.state.cache is managers[0] and second.state.cache is managers[1]

            # 两个应用连的是同一个实例，写入互相可见，但连接与组件各自独立。
            with first.state.application_context.execution():
                await handlers[0].set(key_module.TestCacheKeys.ITEM, "shared", "v")
            with second.state.application_context.execution():
                assert (await handlers[1].get(key_module.TestCacheKeys.ITEM, "shared")).value == "v"
                await handlers[1].delete_all(key_module.TestCacheKeys.ITEM)


async def test_closing_one_application_does_not_affect_the_other(
    config_dir, module_values, key_module
):
    first, second = build_app(config_dir, module_values), build_app(config_dir, module_values)
    async with second.router.lifespan_context(second):
        async with first.router.lifespan_context(first):
            with first.state.application_context.execution():
                first_manager = first.state.application_context.get_bean(CacheManager)
                await first.state.application_context.get_bean(CacheHandler).set(
                    key_module.TestCacheKeys.ITEM, "alive", 1
                )
        assert first_manager.is_ready is False
        with pytest.raises(CacheConnectionException):
            first_manager.get_client("default")

        with second.state.application_context.execution():
            cache = second.state.application_context.get_bean(CacheHandler)
            assert (await cache.get(key_module.TestCacheKeys.ITEM, "alive")).value == 1
            await cache.delete_all(key_module.TestCacheKeys.ITEM)


async def test_cache_components_are_unavailable_after_application_shutdown(
    config_dir, module_values
):
    app = build_app(config_dir, module_values)
    async with app.router.lifespan_context(app):
        context = app.state.application_context
    assert context.container.state is ContainerStateEnum.CLOSED
    assert app.state.cache is None
    with pytest.raises(DiException):
        with context.execution():
            context.get_bean(CacheHandler)


async def test_concurrent_requests_reuse_one_pool_without_cross_talk(
    config_dir, module_values, key_module
):
    app = build_app(config_dir, module_values)
    item = key_module.TestCacheKeys.ITEM

    @app.get("/roundtrip/{identifier}")
    async def roundtrip(identifier: str, cache=Depends(DiDependency(CacheHandler))):
        await cache.set(item, identifier, identifier)
        return {"value": (await cache.get(item, identifier)).value}

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            responses = await asyncio.gather(
                *(client.get(f"/roundtrip/req{index}") for index in range(40))
            )
        assert [item_.json()["value"] for item_ in responses] == [
            f"req{index}" for index in range(40)
        ]
        with app.state.application_context.execution():
            await app.state.application_context.get_bean(CacheHandler).delete_all(item)
