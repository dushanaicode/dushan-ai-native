from contextlib import AsyncExitStack

import pytest

from fixtures.public_web_app import create_public_app
from fixtures.starter_steps import StarterSteps


class TestMonitorServiceIdentity:
    @pytest.mark.parametrize(
        "environ",
        [
            {"SERVER_NAME": "environment-service"},
            {"SERVER_NAME": "environment-service", "SERVER_VERSION": "2.3.4"},
        ],
    )
    async def test_monitor_follows_effective_server_configuration(
        self, config_dir, memory_exporters, environ
    ):
        """仅设置服务环境变量时，追踪资源与最终服务配置一致。"""
        app = create_public_app(
            steps=StarterSteps.without_tenant(),
            base_dir=config_dir(
                {"config": {"models": {"monitor": {"enabled": True, "sampler": "always_on"}}}}
            ),
            environ=environ,
        )
        async with app.router.lifespan_context(app):
            monitor = app.state.monitor
            assert monitor.settings.service_name == app.state.server_settings.name
            assert monitor.settings.service_version == app.state.server_settings.version
            with monitor.span("identity"):
                pass
            await monitor.flush()
            resource = memory_exporters[0].get_finished_spans()[0].resource.attributes
            assert resource["service.name"] == app.state.server_settings.name
            assert resource["service.version"] == app.state.server_settings.version

    async def test_monitor_explicit_overrides_and_applications_are_isolated(
        self, config_dir, memory_exporters
    ):
        """各应用保留自己的服务信息，显式 Monitor 环境变量优先。"""
        base_dir = config_dir({"config": {"models": {"monitor": {"enabled": True}}}})
        async with AsyncExitStack() as stack:
            first = create_public_app(
                steps=StarterSteps.without_tenant(),
                base_dir=base_dir,
                environ={"SERVER_NAME": "first", "SERVER_VERSION": "1"},
            )
            await stack.enter_async_context(first.router.lifespan_context(first))
            second = create_public_app(
                steps=StarterSteps.without_tenant(),
                base_dir=base_dir,
                environ={
                    "SERVER_NAME": "second",
                    "SERVER_VERSION": "2",
                    "MONITOR_SERVICE_NAME": "second-monitor",
                    "MONITOR_SERVICE_VERSION": "2-monitor",
                },
            )
            await stack.enter_async_context(second.router.lifespan_context(second))
            assert first.state.monitor.settings.service_name == "first"
            assert first.state.monitor.settings.service_version == "1"
            assert second.state.monitor.settings.service_name == "second-monitor"
            assert second.state.monitor.settings.service_version == "2-monitor"
