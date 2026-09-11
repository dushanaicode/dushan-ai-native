import pytest
import yaml
from config_factory import ConfigFactory
from pydantic import ValidationError

from framework.common.i18n.core.i18n_options import I18nOptions
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.core.data_paginator import DataPaginator
from framework.common.response.config.response_settings import ResponseSettings
from framework.common.response.core.file_result import FileResult
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_logging.config.log_settings import LogSettings
from framework.starter_logging.core.logger_configurator import LoggerConfigurator
from framework.starter_logging.starter.logging_starter import LoggingStarter
from server.config.application_settings import ApplicationSettings
from server.starter_server import create_app

pytestmark = pytest.mark.unit

CONFIG_FIELDS = [
    (group, name)
    for group, field in ApplicationSettings.model_fields.items()
    for name in field.annotation.model_fields
]


@pytest.mark.parametrize("group,field", CONFIG_FIELDS)
def test_missing_config_field_is_not_replaced_by_a_code_default(config_dir, group, field):
    """逐个删除公共配置字段，确保缺项无法被模型或组件默认值掩盖。"""
    root = config_dir()
    path = root / "application.yaml"
    values = yaml.safe_load(path.read_text(encoding="utf-8"))
    del values[group][field]
    path.write_text(yaml.safe_dump(values, allow_unicode=True), encoding="utf-8")
    with pytest.raises(BootstrapConfigError) as caught:
        BootstrapConfigProvider.load(root, environ={}).get_config(ApplicationSettings)
    assert f"{group}.{field}" in str(caught.value)


@pytest.mark.parametrize("group", tuple(ApplicationSettings.model_fields))
def test_missing_group_does_not_create_default_settings(config_dir, group):
    """缺少整个分组时不创建默认配置模型。"""
    root = config_dir()
    path = root / "application.yaml"
    values = yaml.safe_load(path.read_text(encoding="utf-8"))
    del values[group]
    path.write_text(yaml.safe_dump(values, allow_unicode=True), encoding="utf-8")
    with pytest.raises(BootstrapConfigError, match=group):
        BootstrapConfigProvider.load(root, environ={}).get_config(ApplicationSettings)


def test_configuration_sources_follow_effective_overrides_without_values(config_dir):
    """来源映射与实际覆盖一致，返回副本且不会暴露配置原值。"""
    root = config_dir(
        {"log": {"rotation_size": "11 MB"}},
        dev={"log": {"rotation_size": "12 MB", "retention_info": "2 days"}},
        local={"log": {"rotation_size": "13 MB", "retention_error": "40 days"}},
    )
    provider = BootstrapConfigProvider.load(root, environ={"LOG_ROTATION_SIZE": "14 MB"})
    config = provider.get_config(ApplicationSettings)
    sources = provider.get_sources(ApplicationSettings)
    assert config.log.rotation_size == "14 MB"
    assert config.log.retention_info == "2 days"
    assert config.log.retention_error == "40 days"
    assert sources["log.rotation_size"] == "环境变量 LOG_ROTATION_SIZE"
    assert sources["log.retention_info"] == "application-dev.yaml"
    assert sources["log.retention_error"] == "application-local.yaml"
    assert sources["log.console_level"] == "application.yaml"
    assert "14 MB" not in repr(sources)
    sources["log.rotation_size"] = "changed"
    assert (
        provider.get_sources(LogSettings, prefix="LOG_")["log.rotation_size"]
        == "环境变量 LOG_ROTATION_SIZE"
    )


def test_falsey_values_are_kept_through_yaml_and_environment_overrides(config_dir):
    """零、False、空集合、允许的空串及 null 均保留，不走真值兜底。"""
    root = config_dir(
        {"server": {"root_path": "/base"}, "response": {"download_max_age": 90}},
        dev={
            "server": {"root_path": ""},
            "log": {"compression": None, "file_active_types": []},
            "i18n": {"scopes": []},
        },
    )
    provider = BootstrapConfigProvider.load(
        root,
        environ={
            "RESPONSE_DOWNLOAD_MAX_AGE": "0",
            "PAGE_MAX_SORT_FIELDS": "0",
            "I18N_CACHE_SIZE": "0",
            "I18N_ENABLED": "false",
            "LOG_ENABLE_FILE_OVERALL": "false",
        },
    )
    config = provider.get_config(ApplicationSettings)
    assert config.response.download_max_age == 0
    assert config.page.max_sort_fields == 0
    assert config.i18n.cache_size == 0 and config.i18n.enabled is False
    assert config.i18n.scopes == ()
    assert config.log.enable_file_overall is False and config.log.file_active_types == set()
    assert config.log.compression is None and config.server.root_path == ""


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("server", "name", ""),
        ("log", "root_dir", ""),
        ("server", "port", True),
        ("granian", "workers", True),
        ("granian", "threads", False),
        ("uvicorn", "workers", True),
        ("i18n", "cache_size", False),
        ("i18n", "reload_interval", True),
    ],
)
def test_invalid_empty_values_and_boolean_numbers_fail_with_source(
    config_dir, section, field, value
):
    """不合法空值或布尔数值明确报来源，不能回退为可用默认值。"""
    root = config_dir(local={section: {field: value}})
    with pytest.raises(BootstrapConfigError) as caught:
        BootstrapConfigProvider.load(root, environ={}).get_config(ApplicationSettings)
    assert f"{section}.{field}" in str(caught.value)
    assert "application-local.yaml" in str(caught.value)


def test_unknown_environment_keys_fail_instead_of_silently_using_yaml(config_dir):
    """受管环境变量拼错时明确失败，错误信息不包含原值。"""
    with pytest.raises(BootstrapConfigError) as caught:
        BootstrapConfigProvider.load(
            config_dir(), environ={"LOG_RETENTION_INF0": "private-value"}
        ).get_config(ApplicationSettings)
    assert "LOG_RETENTION_INF0" in str(caught.value)
    assert "private-value" not in str(caught.value)


def test_invalid_environment_value_reports_exact_origin(config_dir):
    """模型校验失败能够定位到最终覆盖的环境变量。"""
    with pytest.raises(BootstrapConfigError) as caught:
        BootstrapConfigProvider.load(
            config_dir(), environ={"PAGE_MAX_SIZE": "private-invalid-value"}
        ).get_config(ApplicationSettings)
    assert "page.max_size" in str(caught.value)
    assert "环境变量 PAGE_MAX_SIZE" in str(caught.value)
    assert "private-invalid-value" not in str(caught.value)


@pytest.mark.parametrize("model", [LogSettings, PageSettings, ResponseSettings, I18nOptions])
def test_standalone_settings_require_explicit_values(model):
    """直接构造组件配置也不能获得另一套隐式默认值。"""
    with pytest.raises(ValidationError):
        model()


@pytest.mark.parametrize("component", [DataPaginator, FileResult, LoggingStarter])
def test_component_cannot_skip_configuration_injection(component):
    """组件不能通过无参构造静默启用代码默认配置。"""
    with pytest.raises(TypeError):
        component()


def test_relative_logging_directory_uses_the_explicit_configuration_root(tmp_path):
    """日志路径取自 YAML 并基于配置目录解析，与进程工作目录无关。"""
    config = ConfigFactory.build(LogSettings, "log")
    configurator = LoggerConfigurator(tmp_path)
    assert configurator._resolve_log_dir(config) == tmp_path / config.root_dir


def test_falsey_configurator_is_not_replaced(tmp_path):
    """调用方提供的假值对象仍被使用，不执行 configurator or 默认对象。"""

    class FalseyConfigurator(LoggerConfigurator):
        def __bool__(self):
            return False

    configurator = FalseyConfigurator(tmp_path)
    starter = LoggingStarter(configurator)
    assert starter._configurator is configurator


def test_application_retains_immutable_sources_for_its_configuration_snapshot(config_dir):
    """运行中的应用保留启动时的来源，查询时不重新加载已变化的文件。"""
    root = config_dir({"page": {"default_size": 2}})
    first = create_app(base_dir=root, environ={"LOG_CONSOLE_LEVEL": "ERROR"}).state.bootstrap
    config_dir({"page": {"default_size": 4}})
    second = create_app(base_dir=root, environ={}).state.bootstrap
    assert first.page_settings.default_size == 2 and second.page_settings.default_size == 4
    assert first.config_sources["log.console_level"] == "环境变量 LOG_CONSOLE_LEVEL"
    assert second.config_sources["log.console_level"] == "application.yaml"
    with pytest.raises(TypeError):
        first.config_sources["log.console_level"] = "changed"
