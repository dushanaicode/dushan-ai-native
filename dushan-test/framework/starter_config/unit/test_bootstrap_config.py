"""配置优先级、输入边界与生产模式验证。"""

import pytest

from framework.common.enums.application_environment_enum import ApplicationEnvironmentEnum
from framework.starter_config.provider.bootstrap_config_provider import (
    BootstrapConfigError,
    BootstrapConfigProvider,
)
from server.config.server.server_settings import ServerSettings


def settings(path, **kwargs):
    """使用显式环境快照，避免测试读取开发者本机配置。"""
    return BootstrapConfigProvider.load(path, **kwargs).get_config(ServerSettings, prefix="SERVER_")


def test_environment_overrides_local_and_profile(config_dir):
    root = config_dir(
        {"SERVER_PORT": 40001}, dev={"SERVER_PORT": 40002}, local={"SERVER_PORT": 40003}
    )
    assert settings(root, environ={}).port == 40003
    assert settings(root, environ={"SERVER_PORT": "40004"}).port == 40004


def test_environment_can_override_model_default(config_dir):
    root = config_dir()
    assert settings(root, environ={"SERVER_LOG_LEVEL": "debug"}).log_level == "DEBUG"


def test_explicit_environment_wins_over_process_environment(config_dir):
    root = config_dir()
    assert (
        settings(root, app_env="test", environ={"SERVER_ENV": "prod"}).env
        == ApplicationEnvironmentEnum.TEST
    )


def test_production_ignores_local_override(config_dir):
    root = config_dir(
        prod={"SERVER_DOCS_ENABLED": False}, local={"SERVER_DEBUG": True, "SERVER_PORT": 49999}
    )
    value = settings(root, app_env="prod", environ={})
    assert value.debug is False
    assert value.port == 48080


@pytest.mark.parametrize("key", ["SERVER_DEBUG", "SERVER_RELOAD", "SERVER_DOCS_ENABLED"])
def test_production_rejects_unsafe_overrides(config_dir, key):
    root = config_dir(prod={"SERVER_DOCS_ENABLED": False})
    with pytest.raises(BootstrapConfigError, match="生产环境必须关闭"):
        settings(root, app_env="prod", environ={key: "true"})


def test_production_requires_profile(config_dir):
    with pytest.raises(BootstrapConfigError, match="application-prod.yaml"):
        settings(config_dir(), app_env="prod", environ={})


@pytest.mark.parametrize("environment", ["../prod", "", "unknown"])
def test_environment_is_not_an_arbitrary_path(config_dir, environment):
    with pytest.raises(BootstrapConfigError, match="SERVER_ENV 无效"):
        settings(config_dir(), app_env=environment, environ={})


@pytest.mark.parametrize("port", ["not-a-port", "0", "65536"])
def test_port_is_validated_without_echoing_input(config_dir, port):
    with pytest.raises(BootstrapConfigError) as error:
        settings(config_dir(), environ={"SERVER_PORT": port})
    assert "port" in str(error.value)
    assert port not in str(error.value)


def test_duplicate_yaml_keys_are_rejected(config_dir):
    root = config_dir()
    (root / "application-dev.yaml").write_text(
        "SERVER_PORT: 40001\nSERVER_PORT: 40002\n", encoding="utf-8"
    )
    with pytest.raises(BootstrapConfigError, match="配置键重复"):
        settings(root, environ={})


def test_yaml_error_does_not_echo_sensitive_value(config_dir):
    root = config_dir()
    secret = "不应出现在错误里的配置原值"
    (root / "application-dev.yaml").write_text("SERVER_NAME: [" + secret, encoding="utf-8")
    with pytest.raises(BootstrapConfigError) as error:
        settings(root, environ={})
    assert secret not in str(error.value)


@pytest.mark.parametrize("content", ["- list-item\n", "1: value\n"])
def test_yaml_requires_string_key_mapping(config_dir, content):
    root = config_dir()
    (root / "application-dev.yaml").write_text(content, encoding="utf-8")
    with pytest.raises(BootstrapConfigError):
        settings(root, environ={})


def test_unknown_server_key_is_rejected(config_dir):
    with pytest.raises(BootstrapConfigError, match="SERVER_POTR"):
        settings(config_dir({"SERVER_POTR": 40000}), environ={})


def test_provider_does_not_share_cached_values(config_dir):
    root = config_dir({"SERVER_PORT": 40001})
    first = BootstrapConfigProvider.load(root, environ={})
    config_dir({"SERVER_PORT": 40002})
    second = BootstrapConfigProvider.load(root, environ={})
    assert first.get_config(ServerSettings, prefix="SERVER_").port == 40001
    assert second.get_config(ServerSettings, prefix="SERVER_").port == 40002


def test_missing_base_file_has_clear_error(tmp_path):
    with pytest.raises(BootstrapConfigError, match="application.yaml"):
        settings(tmp_path, environ={})


def test_docs_cannot_replace_health_route(config_dir):
    with pytest.raises(BootstrapConfigError, match="不能占用 /health"):
        settings(config_dir({"SERVER_DOCS_URL": "/health"}), environ={})


@pytest.mark.parametrize(
    "path", ["https://example.com", "//example.com", "/docs?token=value", "/docs#part"]
)
def test_docs_requires_local_path(config_dir, path):
    with pytest.raises(BootstrapConfigError):
        settings(config_dir({"SERVER_DOCS_URL": path}), environ={})
