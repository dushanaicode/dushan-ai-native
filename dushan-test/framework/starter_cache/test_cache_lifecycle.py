import asyncio

import pytest
from redis.asyncio import Redis

from fixtures.cache_fixtures import REDIS_TARGET, app_values, redis_values, requires_redis
from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.enums.cache_lifecycle_phase_enum import CacheLifecyclePhaseEnum
from framework.starter_cache.exception.cache_connection_exception import CacheConnectionException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_operation_exception import CacheOperationException
from framework.starter_cache.starter.cache_starter import CacheStarter
from server.starter_server import create_app

pytestmark = requires_redis


def admin_client() -> Redis:
    """独立的管理连接，不经过被测连接池，用于观察服务端真实连接数。"""
    return Redis(
        host=REDIS_TARGET["host"],
        port=REDIS_TARGET["port"],
        username=REDIS_TARGET.get("username"),
        password=REDIS_TARGET.get("password"),
        db=0,
        decode_responses=True,
    )


@pytest.fixture
async def redis_proxy():
    """本地 TCP 代理，可以在不影响真实实例的前提下制造连接中断。"""
    connections: list[tuple[asyncio.StreamWriter, asyncio.StreamWriter]] = []

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            REDIS_TARGET["host"], REDIS_TARGET["port"]
        )
        connections.append((writer, upstream_writer))

        async def pump(source: asyncio.StreamReader, target: asyncio.StreamWriter) -> None:
            try:
                while data := await source.read(65536):
                    target.write(data)
                    await target.drain()
            except (ConnectionError, asyncio.CancelledError):
                pass

        await asyncio.gather(
            pump(reader, upstream_writer), pump(upstream_reader, writer), return_exceptions=True
        )

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    def cut() -> None:
        """立刻切断全部已建立的连接，模拟服务端不可达。"""
        for downstream, upstream in connections:
            downstream.close()
            upstream.close()
        connections.clear()

    try:
        yield port, cut
    finally:
        cut()
        server.close()
        await server.wait_closed()


async def test_disabled_cache_starts_the_application_without_any_connection(
    config_dir, module_values
):
    baseline = admin_client()
    try:
        before = int((await baseline.info("clients"))["connected_clients"])
        app = create_app(
            base_dir=config_dir(app_values(redis_values(enabled=False), **module_values)),
            environ={},
        )
        async with app.router.lifespan_context(app):
            assert getattr(app.state, "cache", None) is None
            context = app.state.application_context
            with context.execution():
                manager = context.get_bean(CacheManager)
                assert manager.is_ready is False
                assert manager.phase is CacheLifecyclePhaseEnum.STOPPED
                with pytest.raises(CacheConnectionException) as failure:
                    manager.get_client("default")
        assert failure.value.error_code is CacheErrorCodes.NOT_INITIALIZED
        assert int((await baseline.info("clients"))["connected_clients"]) <= before
    finally:
        await baseline.aclose()


async def test_unreachable_redis_fails_startup_with_connection_error(config_dir, module_values):
    values = redis_values(port=6, socket_connect_timeout_seconds=1.0, socket_timeout_seconds=1.0)
    app = create_app(base_dir=config_dir(app_values(values, **module_values)), environ={})

    with pytest.raises(BaseException) as failure:
        async with app.router.lifespan_context(app):
            pass
    assert "缓存" in str(failure.value) or isinstance(failure.value, CacheConnectionException)


async def test_wrong_redis_data_type_surfaces_as_cache_operation_error(cache_case):
    cache, keys, _ = cache_case
    client = cache.get_client(keys.TestCacheKeys.ITEM)
    await client.lpush(cache.build_full_key(keys.TestCacheKeys.ITEM, "list"), "x")

    with pytest.raises(CacheOperationException) as failure:
        await cache.get(keys.TestCacheKeys.ITEM, "list")
    assert failure.value.__cause__ is not None


async def test_connection_loss_during_operation_is_reported_not_swallowed(
    config_dir, module_values, redis_proxy, key_module, cache_prefix
):
    port, cut = redis_proxy
    values = redis_values(port=port, socket_timeout_seconds=2.0, socket_connect_timeout_seconds=2.0)
    app = create_app(base_dir=config_dir(app_values(values, **module_values)), environ={})
    async with app.router.lifespan_context(app):
        context = app.state.application_context
        with context.execution():
            cache = context.get_bean(CacheHandler)
            await cache.set(key_module.TestCacheKeys.ITEM, "alive", 1)
            assert (await cache.get(key_module.TestCacheKeys.ITEM, "alive")).value == 1

            cut()
            with pytest.raises(CacheOperationException):
                await cache.get(key_module.TestCacheKeys.ITEM, "alive")

            # 代理仍在监听，客户端重新建连后功能恢复，失败不会变成永久降级。
            assert (await cache.get(key_module.TestCacheKeys.ITEM, "alive")).value == 1
            await cache.delete_all(key_module.TestCacheKeys.ITEM)


async def test_application_shutdown_releases_server_side_connections(
    config_dir, module_values, key_module, cache_prefix
):
    baseline = admin_client()
    try:
        before = int((await baseline.info("clients"))["connected_clients"])
        app = create_app(
            base_dir=config_dir(app_values(redis_values(), **module_values)), environ={}
        )
        async with app.router.lifespan_context(app):
            context = app.state.application_context
            with context.execution():
                cache = context.get_bean(CacheHandler)
                # 并发写入迫使连接池真正建立多条连接，而不是复用同一条。
                await asyncio.gather(
                    *(
                        cache.set(key_module.TestCacheKeys.ITEM, f"c{index}", index)
                        for index in range(8)
                    )
                )
                during = int((await baseline.info("clients"))["connected_clients"])
                await cache.delete_all(key_module.TestCacheKeys.ITEM)
            assert app.state.cache.is_ready is True
        assert during > before
        await asyncio.sleep(0.3)
        assert int((await baseline.info("clients"))["connected_clients"]) <= before
        assert app.state.cache is None
    finally:
        await baseline.aclose()


async def test_manager_close_is_idempotent_and_blocks_further_client_access(
    config_dir, module_values
):
    app = create_app(base_dir=config_dir(app_values(redis_values(), **module_values)), environ={})
    async with app.router.lifespan_context(app):
        context = app.state.application_context
        with context.execution():
            manager = context.get_bean(CacheManager)
    assert manager.phase is CacheLifecyclePhaseEnum.STOPPED
    await manager.close()
    assert manager.phase is CacheLifecyclePhaseEnum.STOPPED
    with pytest.raises(CacheConnectionException):
        manager.get_client("default")


async def test_starter_registers_keys_before_opening_connections(
    config_dir, module_values, key_module, cache_prefix
):
    app = create_app(base_dir=config_dir(app_values(redis_values(), **module_values)), environ={})
    async with app.router.lifespan_context(app):
        context = app.state.application_context
        with context.execution():
            starter = context.get_bean(CacheStarter)
            assert starter.is_ready is True
            assert starter.cache_key_registry.is_registered is True
            # 断言本用例声明的三个前缀都已登记；不锁总数，
            # 因为同一应用里的其他框架组件也会声明自己的前缀。
            declared = starter.cache_key_registry.get_all()
            assert {key.key for key in key_module.TestCacheKeys.declared_keys()} <= declared.keys()
            assert all(prefix.startswith(cache_prefix) for prefix in declared if ":" in prefix)


async def test_cache_settings_model_is_registered_and_reflects_yaml_defaults(
    config_dir, module_values
):
    app = create_app(base_dir=config_dir(app_values(redis_values(), **module_values)), environ={})
    async with app.router.lifespan_context(app):
        settings = app.state.application_context.container.configuration.get_config(CacheSettings)
    assert settings.enabled is True
    assert settings.null_value_enabled is True
    assert settings.max_ttl_seconds == 2592000


async def test_concurrency_above_pool_size_queues_instead_of_failing(
    config_dir, module_values, key_module
):
    """连接数是资源上限而不是并发上限：高于池大小的瞬时并发应当排队完成。"""
    values = redis_values(max_connections=2, pool_wait_timeout_seconds=10.0)
    app = create_app(base_dir=config_dir(app_values(values, **module_values)), environ={})
    async with app.router.lifespan_context(app):
        context = app.state.application_context
        with context.execution():
            cache = context.get_bean(CacheHandler)
            await asyncio.gather(
                *(
                    cache.set(key_module.TestCacheKeys.ITEM, f"queue{index}", index)
                    for index in range(40)
                )
            )
            results = await asyncio.gather(
                *(cache.get(key_module.TestCacheKeys.ITEM, f"queue{index}") for index in range(40))
            )
            assert [result.value for result in results] == list(range(40))
            await cache.delete_all(key_module.TestCacheKeys.ITEM)
