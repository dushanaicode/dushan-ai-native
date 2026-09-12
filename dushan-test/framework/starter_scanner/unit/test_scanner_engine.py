import dataclasses
import json
import sys
from pathlib import Path

import pytest
from config_factory import ConfigFactory
from scanner_fixtures import error_source

from framework.common.component.component_metadata import ComponentMetadata
from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.exception.registry.error_code_decorator import error_code
from framework.common.importing.package_locator import PackageLocator
from framework.starter_scanner.config.scanner_config import ScannerConfig
from framework.starter_scanner.core.scan_root import ScanRoot
from framework.starter_scanner.core.scanner_engine import ScannerEngine
from framework.starter_scanner.exception.scanner_exception import ScannerException

pytestmark = pytest.mark.unit
COMPONENT = "from framework.starter_scanner.annotation.scanner_decorator import scanner\n@scanner\nclass Example: pass\n"


def test_error_code_marker_is_immutable_and_rejects_duplicate_declaration():
    @error_code()
    class Codes:
        pass

    metadata = vars(Codes)[ComponentMetadata.ATTRIBUTE]
    assert metadata.component_type is ComponentTypeEnum.ERROR_CODE
    with pytest.raises(dataclasses.FrozenInstanceError):
        metadata.component_type = ComponentTypeEnum.COMPONENT
    with pytest.raises(ValueError, match="重复标记"):
        error_code(Codes)
    with pytest.raises(TypeError, match="只能标记类"):
        error_code(object())


def engine(**overrides):
    return ScannerEngine(ConfigFactory.build(ScannerConfig, "scanner", **overrides))


def test_discovery_filters_reexports_inheritance_and_aliases_with_stable_sources(module_package):
    root = module_package(
        "scan_inventory",
        files={
            "a.py": COMPONENT + "Alias = Example\nclass Inherited(Example): pass\n",
            "b.py": "from .a import Example\n" + error_source("Codes", 8001, "inventory.failure"),
            "dynamic.py": "def __getattr__(name): raise AssertionError('不应求值')\n",
        },
    )
    roots = (
        ScanRoot("inventory", "scan_inventory", root),
        ScanRoot("inventory", "scan_inventory", root),
    )
    first = engine().scan(roots)
    second = engine().scan(tuple(reversed(roots)))
    assert [cls.__name__ for cls in first.get_components()] == ["Example", "Codes"]
    assert first.get_components() == second.get_components()
    assert first is not second and first.definitions is not second.definitions
    assert all(
        item.source == Path(sys.modules[item.component.__module__].__file__).resolve()
        for item in first.definitions
    )
    assert len(first.files) == 4
    assert first.get_components(module="missing") == ()
    assert [
        cls.__name__ for cls in first.get_components(component_type=ComponentTypeEnum.ERROR_CODE)
    ] == ["Codes"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.files = ()
    selected = engine(component_types=["error_code"]).scan(roots)
    assert selected.get_components() == first.get_components(
        component_type=ComponentTypeEnum.ERROR_CODE
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"enabled": False},
        {"component_types": []},
        {"include_packages": []},
        {"include_packages": ["scan_disabled.child"], "exclude_packages": ["scan_disabled"]},
    ],
)
def test_off_and_empty_filters_do_not_locate_or_import(tmp_path, monkeypatch, overrides):
    def forbidden(*args, **kwargs):
        pytest.fail("此配置不应定位扫描根")

    monkeypatch.setattr(PackageLocator, "locate", forbidden)
    result = engine(**overrides).scan((ScanRoot("disabled", "scan_disabled", tmp_path / "absent"),))
    assert result.definitions == result.files == ()


def test_excluded_child_is_pruned_before_import_and_parent_discovery_is_read_only(
    module_package, tmp_path
):
    marker = tmp_path / "disabled.marker"
    parent_marker = tmp_path / "parent.marker"
    side_effect = f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
    root = module_package(
        "scan_prune",
        files={
            "__init__.py": f"from pathlib import Path\nPath({str(parent_marker)!r}).write_text('ok')\n",
            "allowed/a.py": COMPONENT,
            "disabled/__init__.py": side_effect,
            "disabled/b.py": side_effect,
        },
    )
    PackageLocator.locate("scan_prune.allowed", package=True)
    assert not parent_marker.exists()
    result = engine(exclude_packages=["scan_prune.disabled"]).scan(
        (ScanRoot("prune", "scan_prune", root),)
    )
    assert parent_marker.exists() and not marker.exists()
    assert "scan_prune.disabled" not in sys.modules
    assert len(result.get_components()) == 1


def test_include_uses_package_boundaries_and_allows_required_parents(module_package, tmp_path):
    marker = tmp_path / "prefix.marker"
    root = module_package(
        "scan_prefix",
        files={
            "selected/a.py": COMPONENT,
            "selected_extra/__init__.py": f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')",
        },
    )
    result = engine(include_packages=["scan_prefix.selected"]).scan(
        (ScanRoot("prefix", "scan_prefix", root),)
    )
    assert not marker.exists()
    assert [cls.__module__ for cls in result.get_components()] == ["scan_prefix.selected.a"]


@pytest.mark.parametrize(
    "source,reason",
    [
        ("raise RuntimeError('password=private-import-value')", RuntimeError),
        ("class :", SyntaxError),
        (error_source("Bad", True, "bad.failure"), TypeError),
    ],
)
def test_import_and_definition_failures_preserve_causes_and_do_not_affect_successful_result(
    module_package, source, reason
):
    good = module_package("scan_good", files={"a.py": COMPONENT})
    result = engine().scan((ScanRoot("good", "scan_good", good),))
    bad = module_package("scan_bad", files={"z.py": source, "a.py": COMPONENT})
    with pytest.raises(ScannerException) as caught:
        engine().scan((ScanRoot("bad", "scan_bad", bad),))
    assert isinstance(caught.value.__cause__, reason)
    assert "scan_bad.z" in str(caught.value)
    assert "private-import-value" not in str(caught.value)
    assert [cls.__module__ for cls in result.get_components()] == ["scan_good.a"]


def test_invalid_metadata_is_not_silently_filtered(module_package):
    root = module_package(
        "scan_metadata", files={"bad.py": "class Bad:\n    __component_metadata__ = {}\n"}
    )
    with pytest.raises(ScannerException, match="元数据非法"):
        engine(component_types=["error_code"]).scan((ScanRoot("metadata", "scan_metadata", root),))


def test_empty_roots_and_no_marked_classes_are_valid(module_package):
    assert engine().scan(()).definitions == ()
    root = module_package("scan_empty", files={"value.py": "class Unmarked: pass"})
    result = engine().scan((ScanRoot("empty", "scan_empty", root),))
    assert result.definitions == () and len(result.files) == 2


def test_diagnostics_are_optional_bounded_and_do_not_change_discovery(module_package):
    root = module_package(
        "scan_diagnostics",
        files={
            **{f"source_{index}.py": COMPONENT for index in range(5)},
            "excluded/bad.py": "raise RuntimeError('excluded')",
        },
    )
    roots = (ScanRoot("diagnostics", "scan_diagnostics", root),)
    measured = engine(exclude_packages=["scan_diagnostics.excluded"], diagnostic_limit=2).scan(
        roots
    )
    unmeasured = engine(
        exclude_packages=["scan_diagnostics.excluded"], diagnostics_enabled=False
    ).scan(roots)
    assert measured.get_components() == unmeasured.get_components()
    assert unmeasured.diagnostics is None
    assert set(dict(measured.diagnostics.phase_seconds)) == {
        "enumeration",
        "validation",
        "import",
        "collection",
    }
    assert dict(measured.diagnostics.skipped_counts)["excluded_prefix"] == 1
    assert len(measured.diagnostics.slow_imports) == 2
    assert len(measured.diagnostics.skipped_examples) <= 2


def test_same_named_package_is_rejected_before_its_side_effect(
    module_package, tmp_path, monkeypatch
):
    root = module_package("scan_collision", files={"a.py": COMPONENT})
    previous = engine().scan((ScanRoot("collision", "scan_collision", root),))
    other = tmp_path / "other"
    package = other / "scan_collision"
    package.mkdir(parents=True)
    marker = tmp_path / "collision.marker"
    (package / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(other))
    with pytest.raises(ConfigurationException, match="来源必须唯一"):
        engine().scan((ScanRoot("collision", "scan_collision", package),))
    assert not marker.exists() and len(previous.definitions) == 1


@pytest.mark.parametrize("attribute", ["__file__", "__path__", "__spec__"])
def test_loaded_parent_source_is_checked_before_child_import(
    module_package, tmp_path, monkeypatch, attribute
):
    marker = tmp_path / "child.marker"
    root = module_package(
        "scan_parent", files={"a.py": f"from pathlib import Path\nPath({str(marker)!r}).touch()"}
    )
    parent = PackageLocator.import_source("scan_parent", root / "__init__.py")
    if attribute == "__file__":
        monkeypatch.setattr(parent, attribute, str(tmp_path / "other.py"))
    elif attribute == "__path__":
        monkeypatch.setattr(parent, attribute, [str(tmp_path)])
    else:
        monkeypatch.setattr(parent.__spec__, "origin", str(tmp_path / "other.py"))
    with pytest.raises(ConfigurationException, match="不匹配"):
        engine().scan((ScanRoot("parent", "scan_parent", root),))
    assert not marker.exists()


def test_symlink_outside_root_is_rejected_before_execution(module_package, tmp_path):
    root = module_package("scan_links")
    marker = tmp_path / "link.marker"
    outside = tmp_path / "outside.py"
    outside.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()", encoding="utf-8")
    (root / "linked.py").symlink_to(outside)
    with pytest.raises(ScannerException, match="链接"):
        engine().scan((ScanRoot("links", "scan_links", root),))
    assert not marker.exists()


def test_overlapping_roots_deduplicate_but_conflicting_owners_fail(module_package):
    root = module_package("scan_overlap", files={"child/a.py": COMPONENT})
    roots = (
        ScanRoot("one", "scan_overlap", root),
        ScanRoot("one", "scan_overlap.child", root / "child"),
    )
    assert len(engine().scan(roots).definitions) == 1
    with pytest.raises(ScannerException, match="归属冲突"):
        engine().scan((roots[0], ScanRoot("two", "scan_overlap.child", root / "child")))


def test_capacity_records_real_file_count_and_duration(module_package, tmp_path):
    root = module_package(
        "scan_capacity", files={f"part_{index:03}.py": COMPONENT for index in range(150)}
    )
    result = engine().scan((ScanRoot("capacity", "scan_capacity", root),))
    assert len(result.definitions) == 150 and len(result.files) == 151
    assert result.duration_seconds > 0
    (tmp_path / "capacity.json").write_text(
        json.dumps(
            {
                "files": len(result.files),
                "components": len(result.definitions),
                "seconds": result.duration_seconds,
            }
        ),
        encoding="utf-8",
    )
