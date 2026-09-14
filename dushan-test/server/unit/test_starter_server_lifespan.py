import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi.testclient import TestClient

from fixtures.public_web_app import create_public_app
from framework.starter_logging.starter.logging_starter import LoggingStarter
from server.bootstrap.bootstrapper import BootstrapError
from server.bootstrap.step_registry import BootstrapStepSpec
from server.bootstrap.steps.logging_step import configure_logging


def test_health_and_docs_after_startup(config_dir):
    app = create_public_app(base_dir=config_dir(), environ={})
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "ready"
        assert client.get("/docs").status_code == 200
        assert "/health" in client.get("/openapi.json").json()["paths"]
    assert app.state.bootstrap.ready is False
    assert not hasattr(app.state, "server_settings")
    assert app.state.bootstrap.logging_starter.initialized is False


async def test_health_is_not_ready_without_lifespan(config_dir):
    app = create_public_app(base_dir=config_dir(), environ={})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        assert (await client.get("/health")).status_code == 503


def test_production_hides_all_documentation_routes(config_dir):
    app = create_public_app(
        base_dir=config_dir(prod={"server": {"docs_enabled": False}}), app_env="prod", environ={}
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        for path in ("/docs", "/redoc", "/openapi.json"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.json()["code"] == 404
            assert set(response.json()) == {"code", "message", "data", "error"}


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
    app = create_public_app(base_dir=config_dir(), environ={}, steps=steps)
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

    app = create_public_app(
        base_dir=config_dir(),
        environ={},
        steps=[BootstrapStepSpec("资源", opened), BootstrapStepSpec("失败项", broken)],
    )
    with pytest.raises(BootstrapError) as error, TestClient(app):
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

    app = create_public_app(
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

    app = create_public_app(
        base_dir=config_dir(),
        environ={},
        steps=[BootstrapStepSpec("第一项", first), BootstrapStepSpec("第二项", second)],
    )
    with pytest.raises(RuntimeError, match="关闭失败用例"), TestClient(app):
        pass
    assert events == ["第一项已释放"]
    assert app.state.bootstrap.ready is False


async def test_logging_cleanup_failure_does_not_replace_startup_error(config_dir, monkeypatch):
    """日志关闭失败作为附注记录，原启动错误和已释放资源保持可核查。"""
    real_shutdown = LoggingStarter.shutdown

    async def failing_shutdown(self):
        """先释放真实日志资源，再模拟关闭报告失败。"""
        await real_shutdown(self)
        raise RuntimeError("password=cleanup-secret")

    @asynccontextmanager
    async def broken(ctx):
        """模拟日志之后的启动步骤失败。"""
        raise ValueError("原始启动失败")
        yield

    monkeypatch.setattr(LoggingStarter, "shutdown", failing_shutdown)
    application = create_public_app(
        base_dir=config_dir(),
        environ={},
        steps=[BootstrapStepSpec("日志", configure_logging), BootstrapStepSpec("失败步骤", broken)],
    )
    with pytest.raises(BootstrapError) as captured:
        async with application.router.lifespan_context(application):
            pass
    assert isinstance(captured.value.__cause__, ValueError)
    notes = "\n".join(captured.value.__notes__)
    assert "日志清理失败" in notes and "password=***" in notes
    assert "cleanup-secret" not in notes
    assert application.state.bootstrap.logging_starter.initialized is False


def test_multiple_apps_do_not_share_state(config_dir, tmp_path):
    """多个应用各写自己的日志，关闭一个不会移除另一个的输出。"""
    root = config_dir(
        {
            "log": {
                "enable_file_overall": True,
                "file_active_types": ["info"],
                "console_level": "NONE",
                "enqueue": False,
                "compression": None,
            }
        }
    )
    first_dir = tmp_path / "first-logs"
    second_dir = tmp_path / "second-logs"
    first = create_public_app(
        base_dir=root, environ={"SERVER_VERSION": "1", "LOG_ROOT_DIR": str(first_dir)}
    )
    second = create_public_app(
        base_dir=root, environ={"SERVER_VERSION": "2", "LOG_ROOT_DIR": str(second_dir)}
    )
    assert first.state.bootstrap is not second.state.bootstrap
    assert first.state.bootstrap.logger is not second.state.bootstrap.logger
    with TestClient(first) as a:
        assert a.get("/health").json()["data"]["version"] == "1"
        first.state.bootstrap.logger.info("first-before")
        with TestClient(second) as b:
            assert b.get("/health").json()["data"]["version"] == "2"
            second.state.bootstrap.logger.info("second-only")
        first.state.bootstrap.logger.info("first-after")
    first_text = "".join(path.read_text(encoding="utf-8") for path in first_dir.glob("*.log"))
    second_text = "".join(path.read_text(encoding="utf-8") for path in second_dir.glob("*.log"))
    assert "first-before" in first_text and "first-after" in first_text
    assert "second-only" not in first_text
    assert "second-only" in second_text
    assert "first-before" not in second_text and "first-after" not in second_text
