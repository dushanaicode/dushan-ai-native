import pytest
from pydantic import field_validator

from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_monitor.config.monitor_settings import MonitorSettings
from server.config.server.server_settings import ServerSettings


class TestBoundConfigMapping:
    def test_mapping_uses_validated_value_and_preserves_yaml_snapshot(self, config_dir):
        """跨模型映射复用规范化后的启动值，并保留原始 YAML 的值和来源。"""

        class NormalizedServerSettings(ServerSettings):
            @field_validator("name")
            @classmethod
            def normalize_name(cls, value):
                """去掉服务名称首尾空格。"""
                return value.strip()

        bootstrap = BootstrapConfigProvider.load(
            config_dir({"server": {"name": "yaml-name"}}),
            environ={"SERVER_NAME": " normalized-name "},
        )
        before = bootstrap.get_yaml_snapshot()
        settings = bootstrap.get_config(NormalizedServerSettings, prefix="SERVER_")
        provider = ConfigProvider(bootstrap, [MonitorSettings])
        try:
            assert settings.name == "normalized-name"
            assert provider.get_config(MonitorSettings).service_name == settings.name
            assert provider.get_sources(MonitorSettings)["service_name"] == "环境变量 SERVER_NAME"
            assert bootstrap.get_yaml_snapshot() == before
            snapshot, _ = bootstrap.get_bound_snapshot()
            snapshot["server"]["name"] = "modified-copy"
            assert bootstrap.get_bound_snapshot()[0]["server"]["name"] == settings.name
        finally:
            provider.close()

    def test_failed_validation_does_not_publish_bound_values(self, config_dir):
        """校验失败不能改写已绑定启动值。"""

        class InvalidServerSettings(ServerSettings):
            @field_validator("name")
            @classmethod
            def reject_name(cls, value):
                """拒绝服务名称以验证失败路径。"""
                raise ValueError("invalid name")

        bootstrap = BootstrapConfigProvider.load(config_dir(), environ={"SERVER_NAME": "valid"})
        bootstrap.get_config(ServerSettings, prefix="SERVER_")
        before = bootstrap.get_bound_snapshot()
        with pytest.raises(BootstrapConfigError):
            bootstrap.get_config(InvalidServerSettings, prefix="SERVER_")
        assert bootstrap.get_bound_snapshot() == before
