import asyncio
import sys
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from scanner_fixtures import error_source

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app

pytestmark = pytest.mark.unit


def application(config_dir, *packages, enabled=None, environ=None):
    values = {
        "modules": {
            "packages": ["framework", *packages],
            "enabled": ["framework", *(packages if enabled is None else enabled)],
        }
    }
    return create_app(base_dir=config_dir(values), environ={} if environ is None else environ)


def explicit_only(definitions):
    """扫描结果完整且仅含启用模块显式列出的类，同时拒绝缺失与多余定义。"""
    declared = set()
    for module in definitions.modules:
        package = module.definition.package
        for reference in module.definition.definitions:
            relative, name = reference.split(":")
            source = package if relative == "." else f"{package}.{relative}"
            declared.add((module.definition.name, source, name))
    actual = {
        (item.module, item.component.__module__, item.component.__qualname__)
        for item in definitions.scan_result.definitions
    }
    return actual == declared


def test_new_module_is_discovered_registered_and_translated_without_core_changes(
    module_package, config_dir
):
    module_package(
        "scan_account",
        files={
            "definitions/constants/codes.py": error_source("AccountCodes", 8101, "account.failure")
        },
        scan_roots=("definitions.constants",),
        messages={
            "zh-CN": {"account.failure": "账户失败"},
            "en-US": {"account.failure": "Account failed"},
        },
    )
    app = application(config_dir, "scan_account")

    @app.get("/failure")
    def failure():
        raise ServiceException(app.state.bootstrap.definitions.error_codes.get_by_code(8101))

    assert app.state.bootstrap.definitions is None
    with TestClient(app) as client:
        definitions = app.state.bootstrap.definitions
        assert definitions.error_codes.get_by_code(8101).message_key == "account.failure"
        assert any(item.module == "scan_account" for item in definitions.scan_result.definitions)
        assert not explicit_only(definitions)
        response = client.get("/failure", headers={"Accept-Language": "en-US"})
        assert response.status_code == 200
        assert response.json()["code"] == 8101 and response.json()["message"] == "Account failed"
        assert client.get("/health").status_code == 200
    assert app.state.bootstrap.definitions is None
    assert app.state.bootstrap.exception_handler.translator is None


def test_disabled_module_does_not_import_or_read_broken_language_json(
    module_package, config_dir, tmp_path
):
    marker = tmp_path / "disabled.marker"
    root = module_package(
        "scan_disabled_app",
        files={
            "__init__.py": f"from pathlib import Path\nPath({str(marker)!r}).touch()",
            "codes.py": error_source("DisabledCodes", 8102, "disabled.failure"),
        },
        messages={"zh-CN": {}, "en-US": {}},
    )
    (root / "definitions/i18n/en-US.json").write_text("bad JSON", encoding="utf-8")
    app = application(config_dir, "scan_disabled_app", enabled=[])
    with TestClient(app):
        assert app.state.bootstrap.definitions.error_codes.get_by_code(8102) is None
        assert "scan_disabled_app" not in sys.modules and not marker.exists()


def test_scanner_disabled_still_loads_declarations_and_resources_without_traversal(
    config_dir, module_package
):
    module_package(
        "scan_declared",
        files={"danger.py": "raise AssertionError('不应自动导入')"},
        messages={
            "zh-CN": {"resource.available": "可用"},
            "en-US": {"resource.available": "Available"},
        },
        required_keys=("resource.available",),
    )
    app = application(config_dir, "scan_declared", environ={"SCANNER_ENABLED": "false"})
    with TestClient(app):
        definitions = app.state.bootstrap.definitions
        assert [item.definition.name for item in definitions.modules] == [
            "framework",
            "scan_declared",
        ]
        assert explicit_only(definitions)
        assert definitions.scan_result.get_components(module="scan_declared") == ()
        assert (
            definitions.translator.translate_any_scope("resource.available", "en-US") == "Available"
        )
        assert "scan_declared.danger" not in sys.modules
        assert definitions.error_codes.get_by_code(400) is not None


def test_explicit_error_definition_is_loaded_without_automatic_scan(module_package, config_dir):
    module_package(
        "scan_explicit",
        files={
            "codes.py": error_source("Codes", 8450, "explicit.failure"),
            "unused.py": "raise RuntimeError('unused')",
        },
        definitions=("codes:Codes",),
        messages={"zh-CN": {"explicit.failure": "失败"}, "en-US": {"explicit.failure": "Failed"}},
    )
    app = application(config_dir, "scan_explicit", environ={"SCANNER_ENABLED": "false"})
    with TestClient(app):
        result = app.state.bootstrap.definitions
        assert result.error_codes.get_by_code(8450).message_key == "explicit.failure"
        assert len(result.scan_result.get_components(module="scan_explicit")) == 1
        assert explicit_only(result)
        missing = replace(
            result.scan_result,
            definitions=tuple(
                item for item in result.scan_result.definitions if item.module != "scan_explicit"
            ),
        )
        assert not explicit_only(replace(result, scan_result=missing))
        assert not explicit_only(
            replace(result, scan_result=replace(result.scan_result, definitions=()))
        )
        assert [
            path.name for path in result.scan_result.files if path.parent.name == "scan_explicit"
        ] == ["codes.py"]
        assert "scan_explicit.unused" not in sys.modules


@pytest.mark.parametrize("definition", ["codes:Missing", "facade:Alias"])
def test_explicit_missing_or_reexported_class_fails_without_publishing(
    module_package, config_dir, definition
):
    module_package(
        "scan_invalid_explicit",
        definitions=(definition,),
        files={
            "codes.py": error_source("Codes", 8451, "explicit.failure"),
            "facade.py": "from .codes import Codes as Alias\n",
        },
    )
    app = application(config_dir, "scan_invalid_explicit", environ={"SCANNER_ENABLED": "false"})
    with pytest.raises(BootstrapError), TestClient(app):
        pass
    assert app.state.bootstrap.definitions is None


def test_multiple_app_catalogs_resources_and_enabled_state_are_independent(
    module_package, config_dir
):
    for package, message in (("scan_app_a", "First"), ("scan_app_b", "Second")):
        module_package(
            package,
            files={"codes.py": error_source("Codes", 8200, "shared.failure")},
            messages={"zh-CN": {"shared.failure": message}, "en-US": {"shared.failure": message}},
        )
    first = application(config_dir, "scan_app_a")
    second = application(config_dir, "scan_app_b")
    with TestClient(first):
        a = first.state.bootstrap.definitions
        with TestClient(second):
            b = second.state.bootstrap.definitions
            assert (
                a is not b
                and a.scan_result is not b.scan_result
                and a.error_codes is not b.error_codes
            )
            assert a.translator.translate_any_scope("shared.failure", "en-US") == "First"
            assert b.translator.translate_any_scope("shared.failure", "en-US") == "Second"
            assert a.error_codes.get_all_detail()[8200][0].startswith("scan_app_a.")
        assert a.translator.translate_any_scope("shared.failure", "en-US") == "First"
        assert first.state.bootstrap.ready


@pytest.mark.parametrize(
    "failure", ["duplicate_code", "import", "missing_translation", "missing_dependency"]
)
def test_failed_app_publishes_nothing_and_keeps_successful_app_usable(
    module_package, config_dir, failure
):
    good = application(config_dir)
    files = {
        "codes.py": error_source(
            "FailureCodes", 400 if failure == "duplicate_code" else 8300, "failure.key"
        )
    }
    if failure == "import":
        files["z.py"] = "raise RuntimeError('original scanner failure')"
    module_package(
        "scan_failure",
        files=files,
        requires=("absent",) if failure == "missing_dependency" else (),
        messages={
            "zh-CN": {"failure.key": "失败"},
            "en-US": {} if failure == "missing_translation" else {"failure.key": "Failed"},
        },
    )
    bad = application(config_dir, "scan_failure")
    with TestClient(good) as client:
        previous = good.state.bootstrap.definitions
        with pytest.raises(BootstrapError) as caught, TestClient(bad):
            pass
        assert caught.value.__cause__ is not None
        assert bad.state.bootstrap.definitions is None and not bad.state.bootstrap.ready
        assert bad.state.bootstrap.exception_handler.translator is None
        assert not bad.state.bootstrap.logging_starter.initialized
        assert good.state.bootstrap.definitions is previous
        assert client.get("/health").status_code == 200


def test_empty_enabled_list_and_resource_only_module_are_explicit(module_package, config_dir):
    module_package(
        "scan_resource",
        scan_roots=(),
        required_keys=("resource.hello",),
        messages={"zh-CN": {"resource.hello": "你好"}, "en-US": {"resource.hello": "Hello"}},
    )
    empty = application(config_dir, "scan_resource", environ={"MODULES_ENABLED": "[]"})
    with TestClient(empty):
        assert empty.state.bootstrap.definitions.modules == ()
    resource = application(config_dir, "scan_resource")
    with TestClient(resource):
        assert (
            resource.state.bootstrap.definitions.scan_result.get_components(module="scan_resource")
            == ()
        )
        assert (
            resource.state.bootstrap.definitions.translator.translate_any_scope(
                "resource.hello", "en-US"
            )
            == "Hello"
        )


def test_i18n_disabled_does_not_read_module_json_but_still_registers_classes(
    module_package, config_dir
):
    root = module_package(
        "scan_no_language",
        files={"codes.py": error_source("Codes", 8400, "no_language.failure")},
        messages={"zh-CN": {}, "en-US": {}},
    )
    (root / "definitions/i18n/zh-CN.json").write_text("invalid", encoding="utf-8")
    app = application(config_dir, "scan_no_language", environ={"I18N_ENABLED": "false"})
    with TestClient(app):
        assert app.state.bootstrap.definitions.error_codes.get_by_code(8400) is not None


@pytest.mark.parametrize(
    "key,value",
    [
        ("SCANNER_COMPONENT_TYPES", '["unknown"]'),
        ("SCANNER_INCLUDE_PACKAGES", '["bad..package"]'),
        ("SCANNER_EXCLUDE_PACKAGES", "null"),
        ("MODULES_ENABLED", '["x", "x"]'),
        ("MODULES_PACKAGES", '["for"]'),
        ("SCANNER_ENABLED", "private-invalid-value"),
    ],
)
def test_invalid_environment_config_has_field_and_source_without_raw_value(config_dir, key, value):
    with pytest.raises(BootstrapConfigError) as caught:
        application(config_dir, environ={key: value})
    assert key in str(caught.value) and "环境变量" in str(caught.value)
    group, field = key.lower().split("_", 1)
    assert f"{group}.{field}" in str(caught.value)
    assert value not in str(caught.value)


def test_declaration_errors_and_dependency_cycles_precede_import(
    module_package, config_dir, tmp_path
):
    marker = tmp_path / "cycle.marker"
    effect = f"from pathlib import Path\nPath({str(marker)!r}).touch()"
    first = module_package(
        "scan_cycle_a", requires=("scan_cycle_b",), files={"__init__.py": effect}
    )
    module_package("scan_cycle_b", requires=("scan_cycle_a",))
    app = application(config_dir, "scan_cycle_a", "scan_cycle_b")
    with pytest.raises(BootstrapError) as caught, TestClient(app):
        pass
    assert isinstance(caught.value.__cause__, ConfigurationException)
    assert "循环" in str(caught.value.__cause__) and not marker.exists()
    path = first / "module.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('scan_roots = ["."]', 'scan_roots = [".."]'),
        encoding="utf-8",
    )
    with (
        pytest.raises(BootstrapError) as caught,
        TestClient(application(config_dir, "scan_cycle_a")),
    ):
        pass
    assert "module.toml" in str(caught.value.__cause__)


def test_configuration_sources_and_null_empty_values_remain_distinct(config_dir, module_package):
    module_package("scan_filtered", files={"danger.py": "raise AssertionError('不应自动导入')"})
    app = application(
        config_dir,
        "scan_filtered",
        environ={"SCANNER_INCLUDE_PACKAGES": "[]", "SCANNER_COMPONENT_TYPES": "null"},
    )
    ctx = app.state.bootstrap
    assert ctx.scanner_config.include_packages == () and ctx.scanner_config.component_types is None
    assert ctx.config_sources["scanner.include_packages"] == "环境变量 SCANNER_INCLUDE_PACKAGES"
    with TestClient(app):
        assert explicit_only(ctx.definitions)
        assert ctx.definitions.scan_result.get_components(module="scan_filtered") == ()
        assert "scan_filtered.danger" not in sys.modules


def test_module_language_link_cannot_escape_its_declared_package(
    module_package, config_dir, tmp_path
):
    root = module_package("scan_language_link", scan_roots=(), messages={"zh-CN": {}, "en-US": {}})
    resources = root / "definitions/i18n"
    for locale in ("zh-CN", "en-US"):
        (resources / f"{locale}.json").unlink()
    resources.rmdir()
    outside = tmp_path / "outside_language"
    outside.mkdir()
    resources.symlink_to(outside, target_is_directory=True)
    app = application(config_dir, "scan_language_link")
    with pytest.raises(BootstrapError) as caught, TestClient(app):
        pass
    assert "语言资源越界" in str(caught.value.__cause__)
    assert app.state.bootstrap.definitions is None and not app.state.bootstrap.ready


async def test_import_cancellation_propagates_and_releases_real_startup_resources(
    module_package, config_dir
):
    module_package(
        "scan_cancelled",
        files={"cancel.py": "import asyncio\nraise asyncio.CancelledError('scanner-cancelled')"},
    )
    app = application(config_dir, "scan_cancelled")
    with pytest.raises(asyncio.CancelledError, match="scanner-cancelled"):
        async with app.router.lifespan_context(app):
            pytest.fail("取消后的应用不应就绪")
    assert app.state.bootstrap.definitions is None and not app.state.bootstrap.ready
    assert app.state.bootstrap.exception_handler.translator is None
    assert not app.state.bootstrap.logging_starter.initialized
