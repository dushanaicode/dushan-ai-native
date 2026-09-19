import pytest
from pydantic import BaseModel

from framework.common.enums.application_environment_enum import (
    ApplicationEnvironmentEnum,
)
from framework.common.enums.log_level_enum import LogLevelEnum
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_logging.config.log_config_builder import LogConfigBuilder
from framework.starter_logging.definitions.enums.log_file_type_enum import LogFileTypeEnum
from server.config.application_settings import ApplicationSettings
from server.config.server.server_settings import ServerSettings


def settings(path, **kwargs):
    """使用测试传入的环境变量，避免受本机配置影响。"""
    return BootstrapConfigProvider.load(path, **kwargs).get_config(ApplicationSettings).server


def test_environment_overrides_local_and_profile(config_dir):
    root = config_dir(
        {"server": {"port": 40001}},
        dev={"server": {"port": 40002}},
        local={"server": {"port": 40003}},
    )
    assert settings(root, environ={}).port == 40003
    assert settings(root, environ={}).name == "渡山测试服务"
    assert settings(root, environ={"SERVER_PORT": "40004"}).port == 40004


def test_environment_can_override_model_default(config_dir):
    root = config_dir()
    configuration = BootstrapConfigProvider.load(
        root, environ={"LOG_CONSOLE_LEVEL": "ERROR"}
    ).get_config(ApplicationSettings)
    assert configuration.log.console_level is LogLevelEnum.ERROR


def test_log_settings_use_nested_yaml_and_environment(config_dir, monkeypatch):
    """日志阈值只由 log 分组及对应环境变量决定。"""
    root = config_dir({"log": {"console_level": "WARNING", "enable_file_overall": False}})
    configuration = BootstrapConfigProvider.load(root, environ={}).get_config(ApplicationSettings)
    assert configuration.log.console_level is LogLevelEnum.WARNING
    configuration = BootstrapConfigProvider.load(
        root,
        environ={
            "LOG_CONSOLE_LEVEL": "TRACE",
            "LOG_FILE_ACTIVE_TYPES": '["info", "error"]',
        },
    ).get_config(ApplicationSettings)
    assert configuration.log.console_level is LogLevelEnum.TRACE
    assert configuration.log.file_active_types == {
        LogFileTypeEnum.INFO,
        LogFileTypeEnum.ERROR,
    }
    assert configuration.log.enable_file_overall is False
    monkeypatch.setenv("LOG_CONSOLE_LEVEL", "SUCCESS")
    assert (
        LogConfigBuilder.get_config(base_dir=str(root), app_env="dev").console_level
        is LogLevelEnum.SUCCESS
    )


def test_removed_server_log_level_is_rejected(config_dir):
    """旧日志字段按未知配置拒绝，调用方必须迁移到 log.console_level。"""
    root = config_dir({"server": {"log_level": "WARNING"}})
    with pytest.raises(BootstrapConfigError, match=r"server\.log_level"):
        BootstrapConfigProvider.load(root, environ={}).get_config(ApplicationSettings)


def test_invalid_logging_configuration_fails_without_echoing_input(config_dir):
    """错误的日志分组和环境数组在启动前拒绝，错误提示不包含原值。"""
    root = config_dir()
    with pytest.raises(BootstrapConfigError) as error:
        BootstrapConfigProvider.load(
            root, environ={"LOG_FILE_ACTIVE_TYPES": "private-invalid-json"}
        ).get_config(ApplicationSettings)
    assert "private-invalid-json" not in str(error.value)
    root = config_dir({"log": {"unknown_setting": True}})
    with pytest.raises(BootstrapConfigError, match="未声明的配置项"):
        BootstrapConfigProvider.load(root, environ={}).get_config(ApplicationSettings)


def test_explicit_environment_wins_over_process_environment(config_dir):
    root = config_dir()
    assert (
        settings(root, app_env="test", environ={"SERVER_ENV": "prod"}).env
        == ApplicationEnvironmentEnum.TEST
    )


def test_production_ignores_local_override(config_dir):
    root = config_dir(
        prod={"server": {"docs_enabled": False}},
        local={"server": {"debug": True, "port": 49999}},
    )
    value = settings(root, app_env="prod", environ={})
    assert value.debug is False
    assert value.port == 48080


@pytest.mark.parametrize("key", ["SERVER_DEBUG", "SERVER_RELOAD", "SERVER_DOCS_ENABLED"])
def test_production_rejects_unsafe_overrides(config_dir, key):
    root = config_dir(prod={"server": {"docs_enabled": False}})
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
        "server:\n  port: 40001\n  port: 40002\n", encoding="utf-8"
    )
    with pytest.raises(BootstrapConfigError, match="配置键重复"):
        settings(root, environ={})


def test_yaml_error_does_not_echo_sensitive_value(config_dir):
    root = config_dir()
    secret = "不应出现在错误里的配置原值"
    (root / "application-dev.yaml").write_text("server:\n  name: [" + secret, encoding="utf-8")
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
    with pytest.raises(BootstrapConfigError, match=r"server\.potr"):
        settings(config_dir({"server": {"potr": 40000}}), environ={})


def test_provider_does_not_share_cached_values(config_dir):
    root = config_dir({"server": {"port": 40001}})
    first = BootstrapConfigProvider.load(root, environ={})
    config_dir({"server": {"port": 40002}})
    second = BootstrapConfigProvider.load(root, environ={})
    assert first.get_config(ServerSettings, prefix="SERVER_").port == 40001
    assert second.get_config(ServerSettings, prefix="SERVER_").port == 40002


def test_missing_base_file_has_clear_error(tmp_path):
    with pytest.raises(BootstrapConfigError, match="application.yaml"):
        settings(tmp_path, environ={})


def test_docs_cannot_replace_health_route(config_dir):
    with pytest.raises(BootstrapConfigError, match="不能占用 /health"):
        settings(config_dir({"server": {"docs_url": "/health"}}), environ={})


@pytest.mark.parametrize(
    "path", ["https://example.com", "//example.com", "/docs?token=value", "/docs#part"]
)
def test_docs_requires_local_path(config_dir, path):
    with pytest.raises(BootstrapConfigError):
        settings(config_dir({"server": {"docs_url": path}}), environ={})


def test_deep_merge_preserves_siblings_and_replaces_lists(config_dir):
    """检查嵌套合并、列表清空，以及修改结果是否会影响原配置。"""

    class FeatureSettings(BaseModel):
        limits: dict[str, int]
        hosts: list[str]

    class ExtendedSettings(ApplicationSettings):
        feature: FeatureSettings

    root = config_dir(
        {"feature": {"limits": {"read": 10, "write": 5}, "hosts": ["example.com"]}},
        dev={"feature": {"limits": {"read": 20}, "hosts": []}},
    )
    provider = BootstrapConfigProvider.load(root, environ={})
    first = provider.get_config(ExtendedSettings)
    assert first.feature.limits == {"read": 20, "write": 5}
    assert first.feature.hosts == []
    first.feature.limits["write"] = 99
    assert provider.get_config(ExtendedSettings).feature.limits["write"] == 5


def test_environment_uses_existing_names_for_each_group(config_dir):
    provider = BootstrapConfigProvider.load(
        config_dir(),
        environ={
            "SERVER_PORT": "40111",
            "GRANIAN_THREADS": "3",
            "UVICORN_WORKERS": "2",
        },
    )
    result = provider.get_config(ApplicationSettings)
    assert result.server.port == 40111
    assert result.granian.threads == 3
    assert result.uvicorn.workers == 2


def test_environment_can_override_a_deeper_model(config_dir):
    class Limits(BaseModel):
        timeout: int

    class Feature(BaseModel):
        limits: Limits

    class ExtendedSettings(ApplicationSettings):
        feature: Feature

    root = config_dir({"feature": {"limits": {"timeout": 10}}})
    result = BootstrapConfigProvider.load(
        root, environ={"FEATURE_LIMITS_TIMEOUT": "30"}
    ).get_config(ExtendedSettings)
    assert result.feature.limits.timeout == 30


@pytest.mark.parametrize(
    "values,location",
    [
        ({"sever": {"port": 48081}}, "sever"),
        ({"granian": {"thread": 2}}, r"granian\.thread"),
        ({"uvicorn": {"port": 48081}}, r"uvicorn\.port"),
    ],
)
def test_unknown_groups_and_nested_fields_are_rejected(config_dir, values, location):
    with pytest.raises(BootstrapConfigError, match=location):
        settings(config_dir(values), environ={})


@pytest.mark.parametrize("value", [None, "invalid", []])
def test_server_group_cannot_be_replaced_with_a_scalar(config_dir, value):
    with pytest.raises(BootstrapConfigError, match="server 必须是配置分组"):
        settings(config_dir(dev={"server": value}), environ={})


def test_environment_does_not_hide_invalid_group_structure(config_dir):
    with pytest.raises(BootstrapConfigError, match="uvicorn"):
        settings(config_dir({"uvicorn": None}), environ={"UVICORN_WORKERS": "2"})


def test_nested_environment_selects_production_profile(config_dir):
    root = config_dir({"server": {"env": "prod"}}, prod={"server": {"docs_enabled": False}})
    result = settings(root, environ={})
    assert result.env == ApplicationEnvironmentEnum.PRODUCTION
    assert result.docs_enabled is False


def test_overrides_cannot_change_selected_environment(config_dir):
    root = config_dir(dev={"server": {"env": "prod"}}, local={"server": {"env": "staging"}})
    assert settings(root, environ={}).env == ApplicationEnvironmentEnum.DEVELOPMENT


@pytest.mark.parametrize(
    "filename", ["application.yaml", "application-dev.yaml", "application-local.yaml"]
)
def test_flat_yaml_has_explicit_migration_error(config_dir, filename):
    root = config_dir()
    (root / filename).write_text("SERVER_PORT: 48081\n", encoding="utf-8")
    with pytest.raises(BootstrapConfigError, match="小写嵌套配置"):
        settings(root, environ={})


def test_multiple_yaml_documents_are_rejected(config_dir):
    root = config_dir()
    (root / "application-dev.yaml").write_text(
        "server:\n  reload: true\n---\nserver:\n  port: 48081\n", encoding="utf-8"
    )
    with pytest.raises(BootstrapConfigError, match="配置文件格式错误"):
        settings(root, environ={})


def test_ambiguous_environment_names_are_a_declaration_error(config_dir):
    class Child(BaseModel):
        b: int

    class Ambiguous(BaseModel):
        a_b: int
        a: Child

    provider = BootstrapConfigProvider.load(config_dir(), environ={})
    with pytest.raises(BootstrapConfigError, match="X_A_B") as caught:
        provider.get_config(Ambiguous, prefix="X_")
    assert "a_b" in str(caught.value) and "a.b" in str(caught.value)
    # 启动配置的顶层分组就是自举占用的环境命名空间，与 ApplicationSettings 字段一一对应。
    assert {prefix[:-1].lower() for prefix in provider.get_group_prefixes()} == set(
        ApplicationSettings.model_fields
    )
