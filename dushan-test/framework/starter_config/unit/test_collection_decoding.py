import traceback

import pytest
from pydantic import create_model

from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_logging.definitions.enums.log_file_type_enum import LogFileTypeEnum
from server.config.application_settings import ApplicationSettings


@pytest.mark.parametrize(
    "annotation,raw,expected",
    [
        (list[int], "[1, 2]", [1, 2]),
        (tuple[str, ...], '["one", "two"]', ("one", "two")),
        (set[str], '["one", "one"]', {"one"}),
        (frozenset[str], '["one"]', frozenset({"one"})),
        (dict[str, int], '{"one": 1}', {"one": 1}),
        (list[str] | None, "null", None),
        (tuple[str, ...] | None, "[]", ()),
        (dict[str, int] | None, "{}", {}),
        (list[str] | str, '["one"]', '["one"]'),
        (list[str] | str | None, "null", "null"),
        (str | None, "null", "null"),
    ],
)
def test_bootstrap_decodes_declared_collections_without_model_parsers(
    config_dir, annotation, raw, expected
):
    """新增集合字段仅声明类型即可接收环境 JSON，字符串联合不被误解码。"""
    model = create_model("FeatureSettings", value=(annotation, ...))
    provider = BootstrapConfigProvider.load(
        config_dir({"feature": {"value": None}}), environ={"FEATURE_VALUE": raw}
    )
    result = provider.get_config(model, prefix="FEATURE_")
    assert result.value == expected
    assert type(result.value) is type(expected)
    assert provider.get_sources(model, prefix="FEATURE_")["feature.value"] == (
        "环境变量 FEATURE_VALUE"
    )


def test_bootstrap_decodes_all_five_models_and_preserves_empty_and_nullable_values(config_dir):
    """启动集合统一走框架解码，空集合与 null 保留各自语义。"""
    configuration = BootstrapConfigProvider.load(
        config_dir(),
        environ={
            "CONFIG_SOURCE_ORDER": '["yaml", "environment"]',
            "CONFIG_FILES": "[]",
            "MODULES_ENABLED": "[]",
            "SCANNER_INCLUDE_PACKAGES": "null",
            "SCANNER_COMPONENT_TYPES": "[]",
            "SCANNER_IGNORED_DIRECTORIES": '["Temp", "build"]',
            "I18N_SUPPORTED_LOCALES": '["zh-CN", "en-US", "fr-FR"]',
            "I18N_SCOPES": "null",
            "I18N_RESOURCE_ROOTS": "[]",
            "LOG_FILE_ACTIVE_TYPES": "[]",
        },
    ).get_config(ApplicationSettings)
    assert configuration.config.source_order == (
        ConfigSourceEnum.YAML,
        ConfigSourceEnum.ENVIRONMENT,
    )
    assert configuration.config.files == ()
    assert configuration.modules.enabled == ()
    assert configuration.scanner.include_packages is None
    assert configuration.scanner.component_types == ()
    assert configuration.scanner.ignored_directories == ("Temp", "build")
    assert configuration.i18n.supported_locales == ("zh-CN", "en-US", "fr-FR")
    assert configuration.i18n.scopes is None
    assert configuration.i18n.resource_roots == ()
    assert configuration.log.file_active_types == set()


@pytest.mark.parametrize(
    "key,field",
    [
        ("CONFIG_FILES", "config.files"),
        ("MODULES_ENABLED", "modules.enabled"),
        ("SCANNER_INCLUDE_PACKAGES", "scanner.include_packages"),
        ("I18N_SCOPES", "i18n.scopes"),
        ("LOG_FILE_ACTIVE_TYPES", "log.file_active_types"),
    ],
)
@pytest.mark.parametrize("raw", ['["private-value",', '{"private-value": 1}', '"private-value"'])
def test_invalid_collection_json_and_shapes_are_redacted(config_dir, key, field, raw):
    """坏 JSON 和合法 JSON 的错误形状均拒绝，异常链不回显配置原值。"""
    with pytest.raises(BootstrapConfigError) as caught:
        BootstrapConfigProvider.load(config_dir(), environ={key: raw}).get_config(
            ApplicationSettings
        )
    assert field in str(caught.value)
    assert f"环境变量 {key}" in str(caught.value)
    assert "private-value" not in str(caught.value)
    assert "private-value" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize(
    "key,raw,field",
    [
        ("CONFIG_SOURCE_ORDER", '["yaml", "yaml"]', "config.source_order"),
        ("MODULES_ENABLED", '["framework", "framework"]', "modules.enabled"),
        ("MODULES_PACKAGES", '["../private-value"]', "modules.packages"),
        ("SCANNER_INCLUDE_PACKAGES", '["pkg", "pkg"]', "scanner.include_packages"),
        ("SCANNER_EXCLUDE_PACKAGES", '["../pkg"]', "scanner.exclude_packages"),
        ("SCANNER_IGNORED_DIRECTORIES", '["Temp", "temp"]', "scanner.ignored_directories"),
        ("SCANNER_DIAGNOSTIC_LIMIT", "101", "scanner.diagnostic_limit"),
        ("I18N_SUPPORTED_LOCALES", '["zh-CN", "ZH-cn"]', "i18n"),
        ("I18N_SUPPORTED_LOCALES", "[]", "i18n.supported_locales"),
        ("I18N_SCOPES", '[" private-value"]', "i18n"),
        ("I18N_REQUIRED_MESSAGE_KEYS", '[""]', "i18n.required_message_keys"),
        ("LOG_FILE_ACTIVE_TYPES", '["private-value"]', "log.file_active_types"),
        ("MODULES_ENABLED", "null", "modules.enabled"),
    ],
)
def test_collection_decoding_keeps_model_constraints(config_dir, key, raw, field):
    """框架只解码集合，名称、去重、边界和非空限制继续由模型拒绝。"""
    with pytest.raises(BootstrapConfigError) as caught:
        BootstrapConfigProvider.load(config_dir(), environ={key: raw}).get_config(
            ApplicationSettings
        )
    assert field in str(caught.value)
    assert "private-value" not in str(caught.value)


def test_yaml_collection_strings_keep_the_same_declared_decoding(config_dir):
    """迁移模型解析器后，YAML 集合字符串仍通过同一框架入口解码。"""
    configuration = BootstrapConfigProvider.load(
        config_dir(
            {
                "config": {"files": "[]"},
                "modules": {"enabled": '["framework"]'},
                "scanner": {"ignored_directories": '["temp"]'},
                "i18n": {"scopes": '["framework"]'},
                "log": {"file_active_types": '["info"]'},
            }
        ),
        environ={},
    ).get_config(ApplicationSettings)
    assert configuration.config.files == ()
    assert configuration.modules.enabled == ("framework",)
    assert configuration.scanner.ignored_directories == ("temp",)
    assert configuration.i18n.scopes == ("framework",)
    assert configuration.log.file_active_types == {LogFileTypeEnum.INFO}


def test_malformed_yaml_collection_string_retains_source_and_redacts_input(config_dir):
    """YAML 集合解码失败保留文件来源，不回显 JSON 原值。"""
    with pytest.raises(BootstrapConfigError) as caught:
        BootstrapConfigProvider.load(
            config_dir(dev={"modules": {"enabled": '["private-value",'}}), environ={}
        ).get_config(ApplicationSettings)
    assert "modules.enabled" in str(caught.value)
    assert "application-dev.yaml" in str(caught.value)
    assert "private-value" not in "".join(traceback.format_exception(caught.value))
