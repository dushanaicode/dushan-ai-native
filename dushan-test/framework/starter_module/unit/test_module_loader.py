import os
import subprocess
import sys

import pytest
from config_factory import ConfigFactory

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.starter_module.module_loader import ModuleLoader
from framework.starter_module.module_settings import ModuleSettings

pytestmark = pytest.mark.unit


def load(packages, enabled):
    return ModuleLoader.load(
        ConfigFactory.build(ModuleSettings, "modules", packages=packages, enabled=enabled)
    )


def test_ids_are_independent_of_package_names_and_dependencies_are_ordered(module_package):
    module_package("scan_dependent", name="app", requires=("core",))
    module_package("scan_required", name="core")
    result = load(["scan_dependent", "scan_required"], ["app", "core"])
    assert [item.definition.name for item in result] == ["core", "app"]
    assert "scan_dependent" not in sys.modules and "scan_required" not in sys.modules


@pytest.mark.parametrize(
    "case,expected",
    [
        ("duplicate_id", "ID 重复"),
        ("overlap", "范围重叠"),
        ("unknown_enabled", "未声明"),
        ("missing_dependency", "必要依赖未启用"),
    ],
)
def test_invalid_module_relationships_fail_before_import(module_package, case, expected):
    module_package(
        "scan_decl_a", name="a", requires=("missing",) if case == "missing_dependency" else ()
    )
    if case == "overlap":
        second = "scan_decl_a.child"
    else:
        second = "scan_decl_b"
    module_package(second, name="a" if case == "duplicate_id" else "b")
    with pytest.raises(ConfigurationException, match=expected):
        load(["scan_decl_a", second], ["unknown"] if case == "unknown_enabled" else ["a"])
    assert "scan_decl_a" not in sys.modules


@pytest.mark.parametrize(
    "field,old,new",
    [
        ("scan_roots", '["."]', '["../outside"]'),
        ("package", '"scan_bad_decl"', '"other"'),
        ("requires", "[]", '["x", "x"]'),
        ("required_message_keys", "[]", '[""]'),
        ("resource_roots", "[]", '[{path = "../outside", scope = "x", required = true}]'),
    ],
)
def test_invalid_declaration_identifies_field_and_file(module_package, field, old, new):
    root = module_package("scan_bad_decl")
    path = root / "module.toml"
    source = path.read_text(encoding="utf-8").replace(f"{field} = {old}", f"{field} = {new}")
    path.write_text(source, encoding="utf-8")
    with pytest.raises(ConfigurationException) as caught:
        load(["scan_bad_decl"], ["scan_bad_decl"])
    assert str(path) in str(caught.value) and field in str(caught.value)


def test_missing_declaration_and_invalid_toml_keep_original_cause(module_package):
    root = module_package("scan_missing_decl")
    path = root / "module.toml"
    path.unlink()
    with pytest.raises(ConfigurationException) as missing:
        load(["scan_missing_decl"], [])
    assert isinstance(missing.value.__cause__, FileNotFoundError)
    path.write_text('name = "one"\nname = "two"', encoding="utf-8")
    with pytest.raises(ConfigurationException) as invalid:
        load(["scan_missing_decl"], [])
    assert invalid.value.__cause__ is not None and "module.toml" in str(invalid.value)


def test_declaration_symlink_cannot_escape_module(module_package, tmp_path):
    root = module_package("scan_decl_link")
    path = root / "module.toml"
    outside = tmp_path / "outside.toml"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ConfigurationException, match="声明读取失败"):
        load(["scan_decl_link"], ["scan_decl_link"])


@pytest.mark.skipif(os.name != "nt", reason="验证 Windows 目录联接")
def test_windows_junction_package_is_rejected_before_init(module_package, tmp_path):
    root = module_package("scan_junction")
    target = tmp_path / "junction_target"
    target.mkdir()
    marker = tmp_path / "junction.marker"
    (target / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()", encoding="utf-8"
    )
    link = root / "child"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True
    )
    # 把联接直接作为声明包，验证发现入口也不能绕过保护。
    with pytest.raises(ConfigurationException, match="联接"):
        load(["scan_junction.child"], [])
    assert not marker.exists()
