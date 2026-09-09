"""应用就绪状态与资源清理顺序验证。"""

import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi.testclient import TestClient

from server.bootstrap.bootstrapper import BootstrapError
from server.bootstrap.step_registry import BootstrapStepSpec
from server.starter_server import create_app


def test_health_and_docs_after_startup(config_dir):
    app = create_app(base_dir=config_dir(), environ={})
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "ready"
        assert client.get("/docs").status_code == 200
        assert "/health" in client.get("/openapi.json").json()["paths"]
    assert app.state.bootstrap.ready is False
    assert not hasattr(app.state, "server_settings")
    assert not app.state.bootstrap.logger.handlers


async def test_health_is_not_ready_without_lifespan(config_dir):
    app = create_app(base_dir=config_dir(), environ={})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        assert (await client.get("/health")).status_code == 503


def test_production_hides_all_documentation_routes(config_dir):
    app = create_app(
        base_dir=config_dir(prod={"SERVER_DOCS_ENABLED": False}), app_env="prod", environ={}
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404


def test_resources_close_in_reverse_order(config_dir):
    events = []

    def resource(name):
        @asynccontextmanager
        async def run(ctx):
            events.append("启动" + name)
            try:
                yield
            finally:
                events.append("关闭" + name)

        return run

    steps = [BootstrapStepSpec(name, resource(name)) for name in ("一", "二")]
    app = create_app(base_dir=config_dir(), environ={}, steps=steps)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
    assert events == ["启动一", "启动二", "关闭二", "关闭一"]


def test_failed_startup_cleans_previous_resource_and_preserves_cause(config_dir):
    events = []

    @asynccontextmanager
    async def opened(ctx):
        events.append("已分配")
        try:
            yield
        finally:
            events.append("已释放")

    @asynccontextmanager
    async def broken(ctx):
        raise ValueError("启动失败用例")
        yield

    app = create_app(
        base_dir=config_dir(),
        environ={},
        steps=[BootstrapStepSpec("资源", opened), BootstrapStepSpec("失败项", broken)],
    )
    with pytest.raises(BootstrapError) as error:
        with TestClient(app):
            pass
    assert isinstance(error.value.__cause__, ValueError)
    assert events == ["已分配", "已释放"]
    assert app.state.bootstrap.ready is False


async def test_cancellation_is_not_changed_into_normal_startup_error(config_dir):
    events = []

    @asynccontextmanager
    async def opened(ctx):
        try:
            yield
        finally:
            events.append("已释放")

    @asynccontextmanager
    async def cancelled(ctx):
        raise asyncio.CancelledError()
        yield

    app = create_app(
        base_dir=config_dir(),
        environ={},
        steps=[BootstrapStepSpec("资源", opened), BootstrapStepSpec("取消项", cancelled)],
    )
    with pytest.raises(asyncio.CancelledError):
        async with app.router.lifespan_context(app):
            pass
    assert events == ["已释放"]
    assert app.state.bootstrap.ready is False


def test_failed_cleanup_still_releases_other_resources(config_dir):
    events = []

    @asynccontextmanager
    async def first(ctx):
        try:
            yield
        finally:
            events.append("第一项已释放")

    @asynccontextmanager
    async def second(ctx):
        try:
            yield
        finally:
            raise RuntimeError("关闭失败用例")

    app = create_app(
        base_dir=config_dir(),
        environ={},
        steps=[BootstrapStepSpec("第一项", first), BootstrapStepSpec("第二项", second)],
    )
    with pytest.raises(RuntimeError, match="关闭失败用例"):
        with TestClient(app):
            pass
    assert events == ["第一项已释放"]
    assert app.state.bootstrap.ready is False


def test_multiple_apps_do_not_share_state(config_dir):
    root = config_dir()
    first = create_app(base_dir=root, environ={"SERVER_VERSION": "1"})
    second = create_app(base_dir=root, environ={"SERVER_VERSION": "2"})
    assert first.state.bootstrap is not second.state.bootstrap
    assert first.state.bootstrap.logger is not second.state.bootstrap.logger
    with TestClient(first) as a, TestClient(second) as b:
        assert a.get("/health").json()["data"]["version"] == "1"
        assert b.get("/health").json()["data"]["version"] == "2"
