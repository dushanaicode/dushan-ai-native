import hashlib
import json
from pathlib import Path

import pytest
from loguru import logger
from pydantic import ValidationError

from fixtures.config_factory import ConfigFactory
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.starter_i18n.core.catalog import I18nCatalog
from framework.starter_i18n.core.i18n_locale_root import I18nLocaleRoot
from framework.starter_i18n.core.i18n_options import I18nOptions
from framework.starter_i18n.core.loader import I18nLoader
from framework.starter_i18n.core.parser import AcceptLanguageParser
from framework.starter_i18n.core.reloader import I18nReloader
from framework.starter_i18n.core.translator import I18nTranslator
from framework.starter_i18n.core.validator import I18nValidator
from framework.starter_i18n.starter.i18n_starter import I18nStarter
from framework.starter_web.exception.validation_error_mapper import ValidationErrorMapper

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("locale", ["zh-CN", "en-US"])
def test_builtin_resources_match_public_error_contract_and_exclude_unmigrated_modules(
    tmp_path, locale
):
    """内置资源只覆盖公共错误和已接入的字段校验，业务模块文案独立提供。"""
    message_keys = tuple(
        value.message_key
        for value in vars(GlobalErrorCodeConstants).values()
        if isinstance(value, ErrorCode)
    )
    translator = I18nStarter.initialize(
        ConfigFactory.build(I18nOptions, "i18n"), base_dir=tmp_path, message_keys=message_keys
    )
    catalog = translator.catalog
    assert set(catalog.bundles) == {"zh-CN", "en-US"}
    assert set(catalog.bundles[locale]) == {"framework"}
    validation_keys = {f"validation.{key}" for key in ValidationErrorMapper.messages}
    assert set(catalog.bundles[locale]["framework"]) == set(message_keys) | validation_keys
    for message_key in message_keys:
        translated = translator.translate_any_scope(message_key, locale)
        assert translated and translated != message_key
    assert (
        translator.translate_any_scope("cache.error", locale, default="模块尚未接入")
        == "模块尚未接入"
    )


@pytest.fixture
def messages():
    """收集本组 Loguru 事件，不添加文件输出。"""
    records = []
    sink = logger.add(lambda message: records.append(message.record))
    try:
        yield records
    finally:
        logger.remove(sink)


def write_bundle(root: Path, locale: str, data: dict) -> Path:
    """所有资源由调用测试的 tmp_path 提供。"""
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{locale}.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def make_loader(root: Path, **options) -> I18nLoader:
    """创建只读取测试资源目录的加载器。"""
    return I18nLoader(
        options=ConfigFactory.build(I18nOptions, "i18n", include_builtin=False, **options),
        locale_roots=(I18nLocaleRoot(path=root, scope="test", required=True),),
    )


def make_catalog(**options) -> I18nCatalog:
    """提供可区分命中、语言回退及最终提示的最小资源。"""
    return I18nCatalog(
        bundles={
            "zh-CN": {"test": {"hello": "你好", "only.default": "默认语言"}},
            "en-US": {"test": {"hello": "Hello", "template": "Hello {}"}},
        },
        options=ConfigFactory.build(I18nOptions, "i18n", **options),
    )


@pytest.mark.parametrize(
    "values",
    [
        {"unknown_option": True},
        {"default_locale": "fr-FR"},
        {"supported_locales": []},
        {"supported_locales": ["zh-CN", "ZH-cn"]},
        {"supported_locales": ["zh-CN", "../en-US"]},
        {"supported_locales": "zh-CN,en-US"},
        {"supported_locales": '{"locale":"zh-CN"}'},
        {"match_mode": "guess"},
        {"missing_policy": "ignore"},
        {"format_error_policy": "ignore"},
        {"validation_policy": "ignore"},
        {"cache_size": -1},
        {"missing_cache_size": -1},
        {"reload_interval": 0},
        {"reload_interval": float("inf")},
        {"scopes": [""]},
        {"scopes": [" test"]},
        {"required_message_keys": [""]},
        {"required_message_keys": [" account.greeting"]},
    ],
)
def test_options_reject_unknown_and_invalid_configuration(values):
    with pytest.raises(ValidationError):
        ConfigFactory.build(I18nOptions, "i18n", **values)


def test_options_parse_environment_arrays_and_are_immutable(tmp_path):
    values = ConfigFactory.build(
        I18nOptions,
        "i18n",
        supported_locales='["zh-CN", "en-US", "fr-FR"]',
        scopes='["test"]',
        resource_roots=json.dumps([{"path": str(tmp_path), "scope": "test", "required": True}]),
    )
    assert values.supported_locales == ("zh-CN", "en-US", "fr-FR")
    assert values.resource_roots[0].path == tmp_path
    assert values.scopes == ("test",)
    with pytest.raises(ValidationError):
        values.enabled = False


@pytest.mark.parametrize("scope", ["", "../other", "test/other", " test"])
def test_locale_roots_reject_invalid_scope(tmp_path, scope):
    with pytest.raises(ValidationError):
        I18nLocaleRoot(path=tmp_path, scope=scope, required=True)


def test_loader_flattens_and_allows_configured_new_language(tmp_path):
    write_bundle(tmp_path, "zh-CN", {"account": {"greeting": "你好"}})
    write_bundle(tmp_path, "fr-FR", {"account.greeting": "Bonjour"})
    catalog = make_loader(tmp_path, supported_locales=("zh-CN", "fr-FR")).load()
    assert catalog.resolve("account.greeting", "fr-FR", scope="test") == "Bonjour"
    assert catalog.resolve("account.greeting", "zh-CN", scope="test") == "你好"


def test_loader_merges_same_scope_in_root_order(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    write_bundle(first, "en-US", {"account": {"name": "Before", "retained": "Keep"}})
    write_bundle(second, "en-US", {"account.name": "After"})
    loader = I18nLoader(
        options=ConfigFactory.build(I18nOptions, "i18n"),
        locale_roots=tuple(
            I18nLocaleRoot(path=root, scope="account", required=True) for root in (first, second)
        ),
    )
    catalog = loader.load()
    assert catalog.resolve("account.name", "en-US", scope="account") == "After"
    assert catalog.resolve("account.retained", "en-US", scope="account") == "Keep"


@pytest.mark.parametrize(
    "payload",
    [
        b'{"same":"first","same":"second"}',
        b'{"nested":{"same":"first","same":"second"}}',
        b'{"account.name":"first","account":{"name":"second"}}',
        b'{"message": "\xff"}',
        b"[]",
        b'{"message": 42}',
        b'{"message": null}',
        b'{"message": ["hello"]}',
        b'{"message": true}',
        b'{"message": ""}',
        b'{"unfinished":',
    ],
)
def test_loader_rejects_ambiguous_or_invalid_resources(tmp_path, payload):
    path = tmp_path / "en-US.json"
    path.write_bytes(payload)
    with pytest.raises(ConfigurationException) as error:
        make_loader(tmp_path).load()
    assert path.name in str(error.value)


def test_loader_preserves_encoding_failure_cause(tmp_path):
    (tmp_path / "en-US.json").write_bytes(b'{"message":"\xff"}')
    with pytest.raises(ConfigurationException) as error:
        make_loader(tmp_path).load()
    assert isinstance(error.value.__cause__, UnicodeError)


def test_loader_wraps_excessively_deep_json_with_resource_location(tmp_path):
    path = tmp_path / "en-US.json"
    path.write_text('{"nested":' * 2000 + '"value"' + "}" * 2000, encoding="utf-8")
    with pytest.raises(ConfigurationException) as error:
        make_loader(tmp_path).load()
    assert isinstance(error.value.__cause__, RecursionError)
    assert path.name in str(error.value)


def test_loader_rejects_repeated_physical_resource_roots(tmp_path):
    write_bundle(tmp_path, "en-US", {"message": "Value"})
    with pytest.raises(ConfigurationException):
        I18nLoader(
            options=ConfigFactory.build(I18nOptions, "i18n"),
            locale_roots=(
                I18nLocaleRoot(path=tmp_path, scope="first", required=True),
                I18nLocaleRoot(path=tmp_path / ".", scope="second", required=True),
            ),
        ).load()


@pytest.mark.parametrize("key", ["", " ", ".a", "a.", "a..b", "a. .b", "a. b"])
def test_loader_rejects_empty_or_whitespace_key_segments(tmp_path, key):
    write_bundle(tmp_path, "en-US", {key: "Unreachable"})
    with pytest.raises(ConfigurationException):
        make_loader(tmp_path).load()


def test_loading_and_snapshot_ignore_disabled_languages_and_nested_layouts(tmp_path):
    write_bundle(tmp_path, "en-US", {"message": "Visible"})
    (tmp_path / "de-DE.json").write_text("{", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "en-US.json").write_text("{", encoding="utf-8")
    loader = make_loader(tmp_path)
    assert loader.load().resolve("message", "en-US") == "Visible"
    assert len(loader.snapshot()) == 1


def test_loader_required_optional_disabled_and_scope_filters(tmp_path):
    absent = tmp_path / "absent"
    with pytest.raises(ConfigurationException):
        make_loader(absent).load()
    optional = I18nLoader(
        options=ConfigFactory.build(I18nOptions, "i18n"),
        locale_roots=(I18nLocaleRoot(path=absent, scope="optional", required=False),),
    )
    assert not optional.load().bundles
    assert not make_loader(absent, enabled=False).load().bundles
    write_bundle(tmp_path, "en-US", {"message": "visible"})
    assert make_loader(tmp_path, scopes=("test",)).load().resolve("message", "en-US") == "visible"
    assert make_loader(tmp_path, scopes=()).load().resolve("message", "en-US") is None
    assert make_loader(tmp_path, scopes=("other",)).load().resolve("message", "en-US") is None


def test_loader_rejects_cross_scope_duplicate_keys_even_between_languages(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    write_bundle(first, "zh-CN", {"collision": "中文"})
    write_bundle(second, "en-US", {"collision": "English"})
    loader = I18nLoader(
        options=ConfigFactory.build(I18nOptions, "i18n"),
        locale_roots=(
            I18nLocaleRoot(path=first, scope="first", required=True),
            I18nLocaleRoot(path=second, scope="second", required=True),
        ),
    )
    with pytest.raises(ConfigurationException, match="collision"):
        loader.load()


def test_snapshot_uses_content_hash_and_tracks_additions_and_deletions(tmp_path):
    path = write_bundle(tmp_path, "en-US", {"message": "Before"})
    loader = make_loader(tmp_path)
    initial = loader.snapshot()
    assert list(initial.values()) == [hashlib.sha256(path.read_bytes()).hexdigest()]
    catalog, loaded_snapshot = loader.load_version()
    assert loaded_snapshot == initial
    assert catalog.resolve("message", "en-US") == "Before"
    write_bundle(tmp_path, "en-US", {"message": "After!"})
    assert loader.snapshot() != initial
    write_bundle(tmp_path, "zh-CN", {"message": "中文"})
    assert len(loader.snapshot()) == 2
    path.unlink()
    assert len(loader.snapshot()) == 1


def test_catalog_fallback_policy_and_resource_ownership():
    bundles = {"en-US": {"test": {"message": "Original"}}}
    catalog = I18nCatalog(bundles=bundles, options=ConfigFactory.build(I18nOptions, "i18n"))
    bundles["en-US"]["test"]["message"] = "External mutation"
    assert catalog.resolve("message", "en-US") == "Original"
    with pytest.raises(TypeError):
        catalog.bundles["en-US"]["test"]["message"] = "Mutation"
    assert make_catalog().translate("only.default", "en-US") == "默认语言"
    assert (
        make_catalog(fallback_to_default=False).translate("only.default", "en-US", default="Final")
        == "Final"
    )
    assert (
        make_catalog(missing_policy="key").translate("missing", "en-US", default="Final")
        == "missing"
    )
    with pytest.raises(ConfigurationException):
        make_catalog(missing_policy="error").translate("missing", "en-US", default="Final")
    assert (
        make_catalog(enabled=False, missing_policy="error").translate(
            "hello", "en-US", default="Final"
        )
        == "Final"
    )


def test_catalog_scope_lookup_does_not_cross_explicit_scope():
    catalog = make_catalog()
    assert catalog.resolve("hello", "en-US") == "Hello"
    assert catalog.resolve("hello", "en-US", scope="other") is None
    assert catalog.translate(None, "en-US") == ""
    assert catalog.translate("", "en-US", default="Final") == "Final"
    assert catalog.translate("missing", "en-US", default="") == ""


@pytest.mark.parametrize("capacity", [0, 1, 2])
def test_catalog_cache_capacity_is_enforced_and_clear_releases_entries(capacity):
    catalog = make_catalog(cache_size=capacity)
    for key in ("hello", "only.default", "template", "hello"):
        assert catalog.resolve(key, "en-US") is not None
        assert len(catalog._resolve_cache) <= capacity
    catalog.clear_cache()
    assert not catalog._resolve_cache
    assert catalog.resolve("hello", "en-US") == "Hello"


def test_missing_diagnostics_are_bounded_deduplicated_and_optional(messages):
    catalog = make_catalog(missing_cache_size=2, cache_size=0)
    catalog.translate("first", "en-US")
    catalog.translate("first", "en-US")
    assert len([event for event in messages if event["level"].name == "WARNING"]) == 1
    for key in ("second", "third", "fourth"):
        catalog.translate(key, "en-US")
    assert len(catalog.get_missing_keys()) <= 2
    missing = catalog.get_missing_keys()
    missing.clear()
    assert catalog.get_missing_keys()
    catalog.clear_cache()
    assert catalog.translate("hello", "en-US") == "Hello"
    messages.clear()
    silent = make_catalog(log_missing=False, missing_cache_size=0)
    assert silent.translate("missing", "en-US", default="Final") == "Final"
    assert not silent.get_missing_keys()
    assert not [event for event in messages if event["level"].name == "WARNING"]


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "zh-CN"),
        ("", "zh-CN"),
        ("EN-us", "en-US"),
        ("en-GB", "en-US"),
        ("fr;q=0.9,en-US;q=0.8", "fr-FR"),
        ("en-US;q=0.8,zh-CN;q=0.8", "en-US"),
        ("en-GB;q=0.1,en-AU;q=0.9,zh;q=0.5", "en-US"),
        ("en-US;q=0,zh-CN;q=0.5", "zh-CN"),
        ("en-US;q=bad,zh-CN;q=0.5", "zh-CN"),
        ("en-US;q=1.1,zh-CN;q=0.5", "zh-CN"),
        ("en-US;q=-1,zh-CN;q=0.5", "zh-CN"),
        ("en-US;q=NaN,zh-CN;q=0.5", "zh-CN"),
        ("en-US;q=0,*;q=0.8", "zh-CN"),
        ("en-US;q=0,zh-CN;q=0,fr-FR;q=0", "zh-CN"),
        ("xx-ZZ", "zh-CN"),
    ],
)
def test_accept_language_quality_matching_and_fallback(header, expected):
    parser = AcceptLanguageParser(
        ConfigFactory.build(I18nOptions, "i18n", supported_locales=("zh-CN", "en-US", "fr-FR"))
    )
    assert parser.detect_lang(header) == expected


def test_language_matching_mode_is_configurable():
    assert (
        AcceptLanguageParser(
            ConfigFactory.build(I18nOptions, "i18n", match_mode="exact")
        ).detect_lang("en")
        == "zh-CN"
    )
    assert (
        AcceptLanguageParser(
            ConfigFactory.build(I18nOptions, "i18n", match_mode="primary")
        ).detect_lang("en")
        == "en-US"
    )


def test_translator_only_formats_resolved_templates():
    translator = I18nTranslator(
        make_catalog(), AcceptLanguageParser(ConfigFactory.build(I18nOptions, "i18n"))
    )
    assert translator.translate("template", "en-US", scope="test", args=("Ada",)) == "Hello Ada"
    assert translator.translate_any_scope("template", "en-US", args=("Ada",)) == "Hello Ada"
    assert (
        translator.translate_any_scope(
            "missing", "en-US", default="已完成 {提示}", args=("ignored",)
        )
        == "已完成 {提示}"
    )
    assert translator.translate_any_scope("missing", "en-US", default="", args=("ignored",)) == ""
    assert (
        translator.translate_any_scope("template", "en-US", default="No argument") == "No argument"
    )
    assert (
        translator.translate_any_scope("template", "en-US", default="Empty argument", args=())
        == "Empty argument"
    )


@pytest.mark.parametrize("template", ["broken {", "number {:d}", "{missing}", "{1}", "{0.absent}"])
def test_translator_format_errors_preserve_final_default_or_raise_with_cause(template):
    bundles = {"en-US": {"test": {"broken": template}}}
    fallback = ConfigFactory.build(I18nOptions, "i18n")
    translator = I18nTranslator(
        I18nCatalog(bundles=bundles, options=fallback), AcceptLanguageParser(fallback)
    )
    assert (
        translator.translate_any_scope(
            "broken", "en-US", default="Final {unchanged}", args=("text",)
        )
        == "Final {unchanged}"
    )
    assert translator.translate_any_scope("broken", "en-US", args=("text",)) == "broken"
    strict = ConfigFactory.build(I18nOptions, "i18n", format_error_policy="error")
    translator = I18nTranslator(
        I18nCatalog(bundles=bundles, options=strict), AcceptLanguageParser(strict)
    )
    with pytest.raises(ConfigurationException) as error:
        translator.translate_any_scope("broken", "en-US", args=("text",))
    assert error.value.__cause__ is not None


def test_validator_checks_configured_languages_without_fallback(messages):
    catalog = I18nCatalog(
        bundles={"zh-CN": {"test": {"required": "存在"}}},
        options=ConfigFactory.build(I18nOptions, "i18n", validation_policy="warning"),
    )
    assert I18nValidator.validate(catalog, ("required",)) == [("required", "en-US")]
    assert any(event["level"].name == "WARNING" for event in messages)
    strict = I18nCatalog(bundles=catalog.bundles, options=ConfigFactory.build(I18nOptions, "i18n"))
    with pytest.raises(ConfigurationException):
        I18nValidator.validate(strict, ("required",))
    disabled = I18nCatalog(
        bundles={}, options=ConfigFactory.build(I18nOptions, "i18n", validate_translations=False)
    )
    assert I18nValidator.validate(disabled, ("required",)) == []
    messages.clear()
    assert I18nValidator.validate(strict, ()) == []
    assert messages


def test_reloader_tracks_modifications_additions_and_deletions(tmp_path, monkeypatch):
    write_bundle(tmp_path, "en-US", {"hello": "Before"})
    clock = [100.0]
    monkeypatch.setattr("framework.starter_i18n.core.reloader.monotonic", lambda: clock[0])
    loader = make_loader(tmp_path, hot_reload=True, reload_interval=2, validate_translations=False)
    reloader = I18nReloader(loader)
    assert reloader.get_catalog().resolve("hello", "en-US") == "Before"
    write_bundle(tmp_path, "en-US", {"hello": "After"})
    clock[0] += 1
    assert reloader.get_catalog().resolve("hello", "en-US") == "Before"
    clock[0] += 2
    assert reloader.get_catalog().resolve("hello", "en-US") == "After"
    write_bundle(tmp_path, "zh-CN", {"new": "新增"})
    clock[0] += 3
    assert reloader.get_catalog().resolve("new", "zh-CN") == "新增"
    (tmp_path / "en-US.json").unlink()
    clock[0] += 3
    assert reloader.get_catalog().resolve("hello", "en-US") is None


@pytest.mark.parametrize(
    "invalid_json",
    ["{", '{"nested":' * 2000 + '"value"' + "}" * 2000],
    ids=["malformed", "too-deep"],
)
def test_reloader_keeps_last_valid_catalog_after_parse_and_validation_failures(
    tmp_path, monkeypatch, invalid_json
):
    write_bundle(tmp_path, "en-US", {"required": "Before"})
    write_bundle(tmp_path, "zh-CN", {"required": "之前"})
    clock = [100.0]
    monkeypatch.setattr("framework.starter_i18n.core.reloader.monotonic", lambda: clock[0])
    reloader = I18nReloader(make_loader(tmp_path, hot_reload=True), message_keys=("required",))
    original = reloader.get_catalog()
    (tmp_path / "en-US.json").write_text(invalid_json, encoding="utf-8")
    clock[0] += 3
    assert reloader.get_catalog() is original
    write_bundle(tmp_path, "en-US", {"other": "Incomplete"})
    clock[0] += 3
    assert reloader.get_catalog() is original
    write_bundle(tmp_path, "en-US", {"required": "Recovered"})
    clock[0] += 3
    assert reloader.get_catalog().resolve("required", "en-US") == "Recovered"


def test_reloader_does_not_publish_version_changed_during_load(tmp_path, monkeypatch):
    write_bundle(tmp_path, "en-US", {"message": "Initial"})
    clock = [100.0]
    monkeypatch.setattr("framework.starter_i18n.core.reloader.monotonic", lambda: clock[0])
    loader = make_loader(tmp_path, hot_reload=True, validate_translations=False)
    reloader = I18nReloader(loader)
    original = reloader.get_catalog()
    real_load_version = loader.load_version

    def changed_during_load():
        result = real_load_version()
        write_bundle(tmp_path, "en-US", {"message": "Latest"})
        return result

    write_bundle(tmp_path, "en-US", {"message": "Intermediate"})
    monkeypatch.setattr(loader, "load_version", changed_during_load)
    clock[0] += 3
    assert reloader.get_catalog() is original
    monkeypatch.setattr(loader, "load_version", real_load_version)
    clock[0] += 3
    assert reloader.get_catalog().resolve("message", "en-US") == "Latest"


def test_reloader_rejects_intermediate_version_when_file_is_changed_then_restored(
    tmp_path, monkeypatch
):
    write_bundle(tmp_path, "en-US", {"message": "Original"})
    clock = [100.0]
    monkeypatch.setattr("framework.starter_i18n.core.reloader.monotonic", lambda: clock[0])
    loader = make_loader(tmp_path, hot_reload=True, validate_translations=False)
    reloader = I18nReloader(loader)
    original = reloader.catalog
    real_load_version = loader.load_version

    def changed_then_restored():
        write_bundle(tmp_path, "en-US", {"message": "Intermediate B"})
        version = real_load_version()
        write_bundle(tmp_path, "en-US", {"message": "Stable A"})
        return version

    write_bundle(tmp_path, "en-US", {"message": "Stable A"})
    monkeypatch.setattr(loader, "load_version", changed_then_restored)
    clock[0] += 3
    assert reloader.get_catalog() is original
    monkeypatch.setattr(loader, "load_version", real_load_version)
    clock[0] += 3
    assert reloader.get_catalog().resolve("message", "en-US") == "Stable A"


def test_reloader_rejects_invalid_initial_catalog(tmp_path):
    write_bundle(tmp_path, "zh-CN", {"required": "中文"})
    with pytest.raises(ConfigurationException):
        I18nReloader(make_loader(tmp_path, hot_reload=True), message_keys=("required",))
