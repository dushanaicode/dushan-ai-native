import ast
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import httpx
import pytest

from fixtures.public_web_app import create_public_app
from framework.starter_config.config.config_settings import ConfigSettings
from framework.starter_config.spi.config_source_provider import ConfigSourceProvider
from framework.starter_database.spi.data_source_config_provider import DataSourceConfigProvider
from framework.starter_database.starter.database_starter import DatabaseStarter
from framework.starter_di.context.di_task_runner import DiTaskRunner
from framework.starter_web.exception.error_log_recorder import ErrorLogRecorder
from framework.starter_web.spi.access_log_provider import AccessLogProvider
from framework.starter_web.spi.error_log_provider import ErrorLogProvider
from server.bootstrap.steps.framework_spi_step import FrameworkSpiStep


@pytest.fixture
def host_spi_context():
    active = SimpleNamespace(database_scope=False)

    @contextmanager
    def database_scope():
        active.database_scope = True
        try:
            yield
        finally:
            active.database_scope = False

    database = SimpleNamespace(
        settings=SimpleNamespace(dynamic_enabled=False),
        scope=Mock(side_effect=database_scope),
    )
    starter = SimpleNamespace(database=database, attach_source_loader=AsyncMock())
    settings = SimpleNamespace(reload_enabled=False)
    tasks = object()
    providers = {}
    container = Mock(
        get=Mock(
            side_effect={
                DatabaseStarter: starter,
                ConfigSettings: settings,
                DiTaskRunner: tasks,
            }.__getitem__
        ),
        get_optional=Mock(side_effect=providers.get),
    )
    state = SimpleNamespace(database=database, access_log_provider=None, access_log_tasks=None)
    ctx = SimpleNamespace(
        app=SimpleNamespace(state=state),
        definitions=SimpleNamespace(application_context=SimpleNamespace(container=container)),
        exception_handler=SimpleNamespace(error_recorder=object()),
        logger=Mock(),
    )
    return SimpleNamespace(
        ctx=ctx,
        container=container,
        providers=providers,
        database=database,
        starter=starter,
        settings=settings,
        tasks=tasks,
        active=active,
    )


@pytest.mark.parametrize("bound", [False, True])
@pytest.mark.parametrize("failed", [False, True])
async def test_error_recorder_binding_and_restoration(host_spi_context, bound, failed):
    probe = host_spi_context
    previous = probe.ctx.exception_handler.error_recorder
    provider = SimpleNamespace(write=AsyncMock())
    if bound:
        probe.providers[ErrorLogProvider] = provider
    try:
        async with FrameworkSpiStep.run(probe.ctx):
            recorder = probe.ctx.exception_handler.error_recorder
            if bound:
                assert isinstance(recorder, ErrorLogRecorder)
                assert recorder._writer is provider.write
            else:
                assert recorder is previous
            if failed:
                raise RuntimeError("later startup step failed")
    except RuntimeError as error:
        assert failed
        assert str(error) == "later startup step failed"
    assert probe.ctx.exception_handler.error_recorder is previous
    assert probe.container.get_optional.call_args_list.count(call(ErrorLogProvider)) == 1


@pytest.mark.parametrize("reload_enabled", [False, True])
@pytest.mark.parametrize("bound", [False, True])
async def test_config_source_requires_reload_enabled(host_spi_context, reload_enabled, bound):
    probe = host_spi_context
    probe.settings.reload_enabled = reload_enabled

    async def refresh():
        assert probe.active.database_scope

    provider = SimpleNamespace(refresh=AsyncMock(side_effect=refresh))
    if bound:
        probe.providers[ConfigSourceProvider] = provider
    async with FrameworkSpiStep.run(probe.ctx):
        assert not probe.active.database_scope
    assert provider.refresh.await_count == int(reload_enabled and bound)
    assert probe.container.get_optional.call_args_list.count(call(ConfigSourceProvider)) == int(
        reload_enabled
    )
    probe.database.scope.assert_called_once_with()


@pytest.mark.parametrize("dynamic_enabled", [False, True])
@pytest.mark.parametrize("bound", [False, True])
async def test_dynamic_source_requires_enablement_and_binding(
    host_spi_context, dynamic_enabled, bound
):
    probe = host_spi_context
    probe.database.settings.dynamic_enabled = dynamic_enabled
    provider = object()

    async def attach(source):
        assert source is provider
        assert probe.active.database_scope

    probe.starter.attach_source_loader.side_effect = attach
    if bound:
        probe.providers[DataSourceConfigProvider] = provider
    async with FrameworkSpiStep.run(probe.ctx):
        pass
    assert probe.starter.attach_source_loader.await_count == int(dynamic_enabled and bound)
    assert probe.container.get_optional.call_args_list.count(call(DataSourceConfigProvider)) == int(
        dynamic_enabled
    )


@pytest.mark.parametrize("bound", [False, True])
async def test_access_provider_is_resolved_once_and_cache_is_released(host_spi_context, bound):
    probe = host_spi_context
    provider = SimpleNamespace(write=AsyncMock())
    if bound:
        probe.providers[AccessLogProvider] = provider
    async with FrameworkSpiStep.run(probe.ctx):
        assert probe.ctx.app.state.access_log_provider is (provider if bound else None)
        assert probe.ctx.app.state.access_log_tasks is (probe.tasks if bound else None)
    assert probe.ctx.app.state.access_log_provider is None
    assert probe.ctx.app.state.access_log_tasks is None
    assert probe.container.get_optional.call_args_list.count(call(AccessLogProvider)) == 1
    assert probe.container.get.call_args_list.count(call(DiTaskRunner)) == int(bound)


async def test_disabled_di_skips_optional_providers(host_spi_context):
    probe = host_spi_context
    probe.ctx.definitions.application_context = None
    previous = probe.ctx.exception_handler.error_recorder
    async with FrameworkSpiStep.run(probe.ctx):
        assert probe.ctx.exception_handler.error_recorder is previous
        assert probe.ctx.app.state.access_log_provider is None
    probe.container.get.assert_not_called()
    probe.container.get_optional.assert_not_called()
    probe.database.scope.assert_not_called()


async def test_optional_providers_work_without_database(host_spi_context):
    probe = host_spi_context
    probe.ctx.app.state.database = None
    probe.settings.reload_enabled = True
    config = SimpleNamespace(refresh=AsyncMock())
    access = SimpleNamespace(write=AsyncMock())
    error = SimpleNamespace(write=AsyncMock())
    probe.providers.update(
        {ConfigSourceProvider: config, AccessLogProvider: access, ErrorLogProvider: error}
    )
    async with FrameworkSpiStep.run(probe.ctx):
        config.refresh.assert_awaited_once_with()
        assert probe.ctx.app.state.access_log_provider is access
        assert probe.ctx.exception_handler.error_recorder._writer is error.write
    probe.database.scope.assert_not_called()
    assert call(DataSourceConfigProvider) not in probe.container.get_optional.call_args_list
    assert call(DatabaseStarter) not in probe.container.get.call_args_list


@pytest.mark.parametrize("enabled", [False, True])
async def test_host_spi_uses_only_enabled_module_bindings(config_dir, module_package, enabled):
    module_package(
        "probe_host_spi",
        files={
            "access_probe.py": """
from framework.starter_di.decorators.components import service
from framework.starter_web.spi.access_log_provider import AccessLogProvider

@service(interface=AccessLogProvider)
class AccessProbe(AccessLogProvider):
    def __init__(self):
        self.records = []

    async def write(self, record):
        self.records.append(record)
""",
            "error_probe.py": """
from framework.starter_di.decorators.components import service
from framework.starter_web.spi.error_log_provider import ErrorLogProvider

@service(interface=ErrorLogProvider)
class ErrorProbe(ErrorLogProvider):
    async def write(self, record):
        pass
""",
            "config_probe.py": """
from framework.starter_di.decorators.components import service
from framework.starter_config.spi.config_source_provider import ConfigSourceProvider

@service(interface=ConfigSourceProvider)
class ConfigProbe(ConfigSourceProvider):
    def __init__(self):
        self.refresh_calls = 0

    async def refresh(self):
        self.refresh_calls += 1
""",
        },
    )
    app = create_public_app(
        base_dir=config_dir(
            {
                "banner": {"enabled": False},
                "modules": {
                    "packages": ["framework", "probe_host_spi"],
                    "enabled": ["framework", "probe_host_spi"] if enabled else ["framework"],
                },
                "config": {"reload_enabled": True},
            }
        ),
        environ={},
    )
    previous = app.state.bootstrap.exception_handler.error_recorder
    async with app.router.lifespan_context(app):
        with app.state.application_context.execution():
            container = app.state.application_context.container
            access = container.get_optional(AccessLogProvider)
            error = container.get_optional(ErrorLogProvider)
            config = container.get_optional(ConfigSourceProvider)
            assert app.state.access_log_provider is access
            if enabled:
                assert access is not None
                assert app.state.access_log_tasks is container.get(DiTaskRunner)
                assert app.state.bootstrap.exception_handler.error_recorder._writer == error.write
                assert config.refresh_calls == 1
            else:
                assert access is error is config is None
                assert app.state.access_log_tasks is None
                assert app.state.bootstrap.exception_handler.error_recorder is previous
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert response.status_code == 200
        if enabled:
            assert len(access.records) == 1
            assert access.records[0].method == "GET"
            assert access.records[0].route == "/health"
    assert app.state.bootstrap.exception_handler.error_recorder is previous
    assert app.state.access_log_provider is None
    assert app.state.access_log_tasks is None


def test_server_has_no_business_module_imports():
    root = Path(__file__).resolve().parents[3] / "dushan-admin-backend/server"
    violations = []
    for file in root.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_bytes())):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            elif isinstance(node, ast.Import):
                modules = [name.name for name in node.names]
            else:
                continue
            violations.extend(
                f"{file.relative_to(root)}:{node.lineno}:{module}"
                for module in modules
                if module.split(".")[0].startswith("module_")
            )
    assert violations == []
