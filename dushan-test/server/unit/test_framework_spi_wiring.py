import ast
from pathlib import Path

import pytest

from fixtures.public_web_app import create_public_app
from framework.starter_auth.core.auth_service import AuthService
from framework.starter_captcha.core.captcha_service import CaptchaService
from framework.starter_di.definitions.constants.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.spi.monitor_provider import MonitorProvider
from server.bootstrap.bootstrapper import BootstrapError

MONITOR_SOURCE = """
from contextlib import nullcontext
from opentelemetry.context import Context
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.conditional import conditional
from framework.starter_monitor.spi.monitor_provider import MonitorProvider

@framework(interface=MonitorProvider)
@conditional(lambda config: True)
class Probe(MonitorProvider):
    def __init__(self):
        self.calls = []

    @property
    def enabled(self):
        return True

    def span(self, name, attributes=None, **options):
        self.calls.append((name, attributes))
        return nullcontext()

    def extract(self, headers):
        return Context()

    def inject(self, headers=None):
        return {"probe": "injected"}
"""


def test_cross_starter_service_imports_are_absent():
    root = Path(__file__).resolve().parents[3] / "dushan-admin-backend/framework"
    violations = []
    for file in root.rglob("*.py"):
        owner = file.relative_to(root).parts[0]
        for node in ast.walk(ast.parse(file.read_bytes())):
            if isinstance(node, ast.ImportFrom) and node.module:
                target = node.module.split(".")
                if len(target) > 1 and target[0] == "framework" and target[1] != owner:
                    for name in node.names:
                        if name.name.endswith("Service"):
                            violations.append(f"{file.relative_to(root)}:{node.lineno}:{name.name}")
            elif isinstance(node, ast.Import):
                for name in node.names:
                    target = name.name.split(".")
                    if (
                        len(target) > 1
                        and target[0] == "framework"
                        and target[1] != owner
                        and target[-1].endswith("_service")
                    ):
                        violations.append(f"{file.relative_to(root)}:{node.lineno}:{name.name}")
    assert violations == []


async def test_monitor_consumers_load_selected_spi(config_dir, module_package, monkeypatch):
    module_package("probe_monitor", files={"provider.py": MONITOR_SOURCE})
    app = create_public_app(
        base_dir=config_dir(
            {
                "banner": {"enabled": False},
                "modules": {
                    "packages": ["framework", "probe_monitor"],
                    "enabled": ["framework", "probe_monitor"],
                },
                "config": {
                    "models": {
                        "auth": {"tracing_enabled": True},
                        "captcha": {"tracing_enabled": True},
                    }
                },
            }
        ),
        environ={},
    )

    def forbidden(*args, **kwargs):
        pytest.fail("跨组件调用绕过 SPI 直接进入 MonitorService")

    async with app.router.lifespan_context(app):
        with app.state.application_context.execution():
            container = app.state.application_context.container
            provider = container.get(MonitorProvider)
            auth = container.get(AuthService)
            captcha = container.get(CaptchaService)
            assert auth.monitor is provider and captcha.monitor is provider
            with monkeypatch.context() as patch:
                patch.setattr(MonitorService, "current", forbidden)
                patch.setattr(MonitorService, "span", forbidden)
                with auth._span("test", "begin"), captcha._span("create"):
                    pass
            assert provider.calls == [
                ("auth.begin", {"auth.source": "test"}),
                ("captcha.create", {"captcha.provider": captcha.settings.provider}),
            ]


async def test_ambiguous_spi_providers_block_startup(config_dir, module_package):
    module_package(
        "ambiguous_monitor",
        files={
            "one.py": MONITOR_SOURCE,
            "two.py": MONITOR_SOURCE.replace("class Probe(", "class OtherProbe("),
        },
    )
    app = create_public_app(
        base_dir=config_dir(
            {
                "banner": {"enabled": False},
                "modules": {
                    "packages": ["framework", "ambiguous_monitor"],
                    "enabled": ["framework", "ambiguous_monitor"],
                },
            }
        ),
        environ={},
    )
    with pytest.raises(BootstrapError) as failure:
        async with app.router.lifespan_context(app):
            pytest.fail("多个有效 SPI 实现不应被猜测选择")
    assert isinstance(failure.value.__cause__, DiException)
    assert failure.value.__cause__.error_code is DiErrorCodes.DUPLICATE_BINDING
    assert not app.state.bootstrap.ready
