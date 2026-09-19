import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from fixtures.config_factory import ConfigFactory
from framework.starter_scanner.config.scanner_config import ScannerConfig
from framework.starter_scanner.core.scan_root import ScanRoot
from framework.starter_scanner.core.scanner_engine import ScannerEngine
from framework.starter_scanner.definitions.constants.scanner_error_codes import ScannerErrorCodes
from framework.starter_scanner.exception.scanner_exception import ScannerException

pytestmark = pytest.mark.unit
COMPONENT = "from framework.starter_scanner.annotation.scanner_decorator import scanner\n@scanner\nclass Example: pass\n"


def engine(**overrides):
    return ScannerEngine(ConfigFactory.build(ScannerConfig, "scanner", **overrides))


def modules(result):
    return sorted(cls.__module__ for cls in result.get_components())


def test_ignored_directories_come_from_configuration_and_prune_before_import(
    module_package, tmp_path
):
    marker = tmp_path / "temp.marker"
    root = module_package(
        "scan_ignore",
        files={
            "temp/__init__.py": f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
            "temp/a.py": COMPONENT,
            "Build/b.py": COMPONENT,
            "__pycache__/junk.pyc": "",
        },
    )
    roots = (ScanRoot("ignore", "scan_ignore", root),)

    preexisting_cache = set(root.rglob("__pycache__"))

    def clean_bytecode_cache():
        # 前一轮扫描真实导入会生成新的 __pycache__，下一轮收集前清掉新增目录；
        # 夹具自带的 __pycache__（含 junk.pyc）用于默认忽略目录计数，必须保留。
        for cache in set(root.rglob("__pycache__")) - preexisting_cache:
            shutil.rmtree(cache)

    clean_bytecode_cache()
    default = engine().scan(roots)
    assert not marker.exists() and "scan_ignore.temp" not in __import__("sys").modules
    assert modules(default) == ["scan_ignore.Build.b"]
    assert dict(default.diagnostics.skipped_counts)["ignored_directory"] == 2
    assert ("ignored_directory", "scan_ignore.temp") in default.diagnostics.skipped_examples
    clean_bytecode_cache()
    case_insensitive = engine(ignored_directories=["build", "TEMP"]).scan(roots)
    assert modules(case_insensitive) == [] and not marker.exists()
    assert dict(case_insensitive.diagnostics.skipped_counts)["ignored_directory"] == 2
    clean_bytecode_cache()
    everything = engine(ignored_directories=[]).scan(roots)
    assert marker.exists()
    assert modules(everything) == ["scan_ignore.Build.b", "scan_ignore.temp.a"]
    skipped = dict(everything.diagnostics.skipped_counts)
    assert "ignored_directory" not in skipped and skipped["not_python_package"] == 1


def test_scan_root_itself_is_not_subject_to_ignore_rules(module_package):
    root = module_package("scan_root_temp.temp", files={"a.py": COMPONENT})
    result = engine(ignored_directories=["temp"]).scan(
        (ScanRoot("temp", "scan_root_temp.temp", root),)
    )
    assert modules(result) == ["scan_root_temp.temp.a"]


def test_hidden_entries_are_always_skipped_before_any_validation(module_package, tmp_path):
    marker = tmp_path / "hidden.marker"
    root = module_package(
        "scan_hidden",
        files={
            ".cache/__init__.py": f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
            ".cache/a.py": COMPONENT,
            "a.py": COMPONENT,
        },
    )
    result = engine(ignored_directories=[]).scan((ScanRoot("hidden", "scan_hidden", root),))
    assert not marker.exists() and modules(result) == ["scan_hidden.a"]
    assert dict(result.diagnostics.skipped_counts)["hidden_path"] == 1
    assert any(
        reason == "hidden_path" and name.endswith(".cache")
        for reason, name in result.diagnostics.skipped_examples
    )


@pytest.mark.parametrize(
    "value,message",
    [
        (["temp", "Temp"], "不允许重复项"),
        (["a/b"], "单层目录名"),
        (["..\\x"], "单层目录名"),
        ([""], "单层目录名"),
        (["."], "单层目录名"),
        ("temp", "JSON 数组"),
        (None, "tuple"),
    ],
)
def test_ignored_directories_configuration_is_validated(value, message):
    with pytest.raises(ValidationError) as caught:
        ConfigFactory.build(ScannerConfig, "scanner", ignored_directories=value)
    assert message in str(caught.value)


def test_ignored_directories_accept_environment_json_arrays():
    config = ConfigFactory.build(ScannerConfig, "scanner", ignored_directories='["Temp", "build"]')
    assert config.ignored_directories == ("Temp", "build")
    assert ConfigFactory.build(ScannerConfig, "scanner").ignored_directories == (
        "__pycache__",
        "temp",
    )


def test_missing_or_non_directory_scan_root_reports_location_and_cause(tmp_path):
    absent = tmp_path / "absent_root"
    with pytest.raises(ScannerException) as caught:
        engine().scan((ScanRoot("absent_module", "scan_absent", absent),))
    assert caught.value.error_code == ScannerErrorCodes.SCANNER_CONFIG_ERROR
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    message = str(caught.value)
    assert "scan_absent" in message and str(absent) in message and "absent_module" in message
    file_root = tmp_path / "file_root.py"
    file_root.write_text("", encoding="utf-8")
    with pytest.raises(ScannerException) as not_directory:
        engine().scan((ScanRoot("file_module", "scan_file", file_root),))
    assert not_directory.value.error_code == ScannerErrorCodes.SCANNER_CONFIG_ERROR
    assert "不是目录" in str(not_directory.value) and "scan_file" in str(not_directory.value)
    disabled = engine(enabled=False).scan((ScanRoot("absent_module", "scan_absent", absent),))
    assert disabled.definitions == ()


def test_unreadable_directory_and_vanished_file_report_package_and_cause(module_package):
    root = module_package("scan_unreadable", files={"locked/a.py": COMPONENT, "gone.py": COMPONENT})
    locked = (root / "locked").resolve()
    original_iterdir, original_resolve = Path.iterdir, Path.resolve

    def iterdir(self):
        if self == locked:
            raise PermissionError(13, "access denied", str(self))
        return original_iterdir(self)

    def resolve(self, strict=False):
        if strict and self.name == "gone.py":
            raise FileNotFoundError(2, "vanished", str(self))
        return original_resolve(self, strict)

    roots = (ScanRoot("unreadable", "scan_unreadable", root),)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, "iterdir", iterdir)
        with pytest.raises(ScannerException) as unreadable:
            engine().scan(roots)
    assert unreadable.value.error_code == ScannerErrorCodes.SCANNER_CONFIG_ERROR
    assert isinstance(unreadable.value.__cause__, PermissionError)
    assert "scan_unreadable.locked" in str(unreadable.value)
    assert str(locked) in str(unreadable.value)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, "resolve", resolve)
        with pytest.raises(ScannerException) as vanished:
            engine().scan(roots)
    assert vanished.value.error_code == ScannerErrorCodes.SCANNER_CONFIG_ERROR
    assert isinstance(vanished.value.__cause__, FileNotFoundError)
    assert "scan_unreadable.gone" in str(vanished.value)
    assert modules(engine().scan(roots)) == ["scan_unreadable.gone", "scan_unreadable.locked.a"]
