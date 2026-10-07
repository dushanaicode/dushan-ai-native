import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest
from fastapi import Depends, WebSocket
from fastapi.testclient import TestClient
from sqlalchemy import literal, select
from sqlalchemy.engine import make_url

from fixtures.cache_fixtures import redis_values, requires_redis
from fixtures.config_factory import ConfigFactory
from fixtures.database_fixtures import TARGETS
from fixtures.public_web_app import create_public_app
from fixtures.starter_steps import StarterSteps
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.starter.cache_starter import CacheStarter
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_database.starter.database_starter import DatabaseStarter
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_di.definitions.constants.di_error_codes import DiErrorCodes
from framework.starter_di.definitions.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.exception.di_exception import DiException
from server.bootstrap.bootstrap_error import BootstrapError
from server.bootstrap.bootstrap_step_spec import BootstrapStepSpec
from server.bootstrap.steps.cache_step import CacheStep

pytestmark = requires_redis


@pytest.fixture(
    params=[target for target in TARGETS if target["url"]] or [None],
    ids=lambda target: "unconfigured" if target is None else target["name"],
)
def resource_app(request, config_dir, monkeypatch):
    """复用真实实例配置，观察正式资源步骤，不替换连接或 I/O。"""
    if request.param is None:
        pytest.skip("需要 DUSHAN_DATABASE_TEST_URLS 指定真实数据库")
    closed = []
    close_database, close_cache = DatabaseStarter.close, CacheStarter.close

    async def database_close(starter):
        closed.append("database")
        await close_database(starter)

    async def cache_close(starter):
        closed.append("cache")
        await close_cache(starter)

    monkeypatch.setattr(DatabaseStarter, "close", database_close)
    monkeypatch.setattr(CacheStarter, "close", cache_close)

    def make(*, missing_database=False, extra_steps=()):
        database = ConfigFactory.values()["config"]["models"]["database"]
        url = make_url(request.param["url"])
        if missing_database:
            url = url.set(database=f"missing_di_{uuid4().hex}")
        database.update(enabled=True, health_check_enabled=False, slow_query_enabled=False)
        database["sources"] = [
            dict(
                name="primary",
                url=url.render_as_string(hide_password=False),
                role="primary",
                weight=100,
                pool=None,
                tls=None,
            )
        ]
        resources = {"closed": closed}

        @asynccontextmanager
        async def checkpoint(ctx):
            application = ctx.definitions.application_context
            resources.update(
                application=application,
                cache=application.get_bean(CacheManager),
                database=application.get_bean(SessionProvider),
                configuration=ctx.definitions.configuration,
            )
            assert application.state is ApplicationStateEnum.STARTING and not ctx.ready
            assert await resources["cache"].get_default_client().ping()
            assert not resources["database"].is_ready
            try:
                yield
            finally:
                # 数据库步骤先退出，缓存仍供资源收尾使用，DI 与配置最后关闭。
                assert not resources["database"].is_ready
                assert resources["cache"].is_ready
                assert await resources["cache"].get_default_client().ping()
                assert resources["configuration"].revision >= 0

        steps = []
        for step in StarterSteps.without_tenant():
            steps.append(step)
            if step.handler is CacheStep.run:
                steps.append(
                    BootstrapStepSpec("真实资源关闭顺序检查", checkpoint, requires_di=True)
                )
        app = create_public_app(
            base_dir=config_dir(
                {
                    "banner": {"enabled": False},
                    "server": {"root_path": "/api"},
                    "config": {"models": {"cache": redis_values(), "database": database}},
                }
            ),
            environ={},
            steps=(*steps, *extra_steps),
        )
        return app, resources

    return make


def assert_closed(app, resources):
    assert resources["closed"] == ["database", "cache"]
    application = resources["application"]
    assert application.state is ApplicationStateEnum.CLOSED
    assert application.container.state is ContainerStateEnum.CLOSED
    assert application.get_statistics()["executions"] == 0
    assert application.tasks.active_count == 0
    assert not resources["database"].is_ready and not resources["cache"].is_ready
    assert app.state.database is None and app.state.cache is None
    assert not app.state.bootstrap.ready
    with pytest.raises(BootstrapConfigError):
        _ = resources["configuration"].revision


async def roundtrip(database, cache):
    assert database is ApplicationContext.lookup(
        SessionProvider
    ) and cache is ApplicationContext.lookup(CacheManager)
    async with database.read_session() as session:
        value = await session.scalar(select(literal(7)))
    client = cache.get_default_client()
    key = f"di-final:{uuid4().hex}"
    try:
        await client.set(key, value, ex=60)
        return {"value": int(await client.get(key))}
    finally:
        await client.delete(key)


def test_http_and_websocket_use_real_resources_and_root_path(resource_app):
    app, resources = resource_app()

    @app.get("/resources")
    async def route(
        database=Depends(DiDependency(SessionProvider)), cache=Depends(DiDependency(CacheManager))
    ):
        return await roundtrip(database, cache)

    @app.websocket("/socket")
    async def socket(
        websocket: WebSocket,
        database=Depends(DiDependency(SessionProvider)),
        cache=Depends(DiDependency(CacheManager)),
    ):
        await websocket.accept()
        await websocket.send_json(await roundtrip(database, cache))
        await websocket.close()

    with TestClient(app, root_path="/api") as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/resources").json() == {"value": 7}
        with client.websocket_connect("/api/socket") as websocket:
            assert websocket.receive_json() == {"value": 7}
    assert_closed(app, resources)


@pytest.mark.parametrize("cancel_host", [False, True])
async def test_drain_preserves_real_resources_through_commit_callback(resource_app, cancel_host):
    app, resources = resource_app()
    ready, stop, working = asyncio.Event(), asyncio.Event(), asyncio.Event()
    release, callback_entered, finish_callback = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def host():
        async with app.router.lifespan_context(app):
            ready.set()
            await stop.wait()

    hosting = asyncio.create_task(host())
    work = None
    try:
        await asyncio.wait_for(ready.wait(), 10)
        application = resources["application"]
        database, cache = resources["database"], resources["cache"]

        async def after_commit():
            assert await roundtrip(database, cache) == {"value": 7}
            callback_entered.set()
            await finish_callback.wait()
            assert await roundtrip(database, cache) == {"value": 7}

        async def transaction():
            async with database.transaction() as session:
                assert await session.scalar(select(literal(1))) == 1
                database.after_commit(after_commit, required=False)
                working.set()
                await release.wait()
                assert await session.scalar(select(literal(2))) == 2

        work = application.tasks.create_task(transaction)
        await asyncio.wait_for(working.wait(), 5)
        stop.set()
        async with asyncio.timeout(5):
            while application.state is not ApplicationStateEnum.DRAINING:
                await asyncio.sleep(0.01)
        if cancel_host:
            hosting.cancel("真实资源宿主取消")
            await asyncio.sleep(0.05)
        assert not hosting.done() and resources["closed"] == []
        with pytest.raises(DiException) as rejected:
            application.tasks.create_task(lambda: None)
        assert rejected.value.error_code == DiErrorCodes.NOT_READY
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            assert (await client.get("/api/health")).status_code == 503
        release.set()
        await asyncio.wait_for(callback_entered.wait(), 5)
        assert database.is_ready and cache.is_ready
        assert not hosting.done() and resources["closed"] == []
        finish_callback.set()
        await asyncio.wait_for(work, 5)
        if cancel_host:
            with pytest.raises(asyncio.CancelledError, match="真实资源宿主取消"):
                await asyncio.wait_for(hosting, 5)
        else:
            await asyncio.wait_for(hosting, 5)
        assert_closed(app, resources)
    finally:
        stop.set()
        release.set()
        finish_callback.set()
        await asyncio.gather(hosting, *(() if work is None else (work,)), return_exceptions=True)


@pytest.mark.parametrize("failure", ["database", "after_resources"])
async def test_startup_failure_rolls_back_real_resources(resource_app, failure):
    original = RuntimeError("真实资源就绪后的启动失败")

    @asynccontextmanager
    async def fail(ctx):
        assert await roundtrip(ctx.app.state.database, ctx.app.state.cache) == {"value": 7}
        assert not ctx.ready
        raise original
        yield

    app, resources = resource_app(
        missing_database=failure == "database",
        extra_steps=(BootstrapStepSpec("启动失败注入", fail, requires_di=True),),
    )
    with pytest.raises(BootstrapError) as caught:
        async with app.router.lifespan_context(app):
            pytest.fail("失败启动不能进入业务就绪状态")
    if failure == "after_resources":
        assert caught.value.__cause__ is original
    else:
        assert isinstance(caught.value.__cause__, DatabaseException)
    assert_closed(app, resources)


async def test_database_cleanup_failure_still_closes_cache_di_and_config(resource_app, monkeypatch):
    app, resources = resource_app()
    original = ValueError("真实数据库释放后的清理失败")
    close_database = DatabaseStarter.close

    async def fail_close(starter):
        await close_database(starter)
        raise original

    monkeypatch.setattr(DatabaseStarter, "close", fail_close)
    with pytest.raises(ExceptionGroup) as caught:
        async with app.router.lifespan_context(app):
            with resources["application"].execution():
                assert await roundtrip(resources["database"], resources["cache"]) == {"value": 7}
    assert caught.value.subgroup(lambda error: error is original) is not None
    assert_closed(app, resources)
