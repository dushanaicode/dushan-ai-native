"""在 -I -S 子进程验证已安装 wheel，显式注入依赖目录，绝不处理 editable .pth。"""

import importlib
import json
import sys
from pathlib import Path


def main():
    installation, dependencies, application_root, output = map(Path, sys.argv[1:])
    sys.path[:0] = [str(installation), str(application_root)]
    sys.path.append(str(dependencies))

    from fastapi.testclient import TestClient

    import framework
    from framework.common.enums.component_type_enum import ComponentTypeEnum
    from framework.starter_scanner.exception.scanner_error_codes import ScannerErrorCodes
    from server.starter_server import create_app

    assert Path(framework.__file__).resolve().is_relative_to(installation)
    imported = []
    for path in sorted((installation / "framework").rglob("*.py")):
        if path.name == "__init__.py":
            continue
        name = ".".join(path.relative_to(installation).with_suffix("").parts)
        module = importlib.import_module(name)
        assert Path(module.__file__).resolve() == path.resolve(), name
        imported.append(name)
    app = create_app(
        base_dir=application_root,
        environ={
            "LOG_ENABLE_FILE_OVERALL": "false",
            "LOG_CONSOLE_LEVEL": "NONE",
            "BANNER_ENABLED": "false",
        },
    )
    with TestClient(app) as client:
        snapshot = app.state.bootstrap.definitions
        assert client.get("/health").status_code == 200
        assert (
            snapshot.error_codes.get_by_code(ScannerErrorCodes.SCANNER_ERROR.code)
            == ScannerErrorCodes.SCANNER_ERROR
        )
        assert (
            len(snapshot.scan_result.get_components(component_type=ComponentTypeEnum.ERROR_CODE))
            == 3
        )
        assert snapshot.application_context is not None
        assert all(path.is_relative_to(installation) for path in snapshot.scan_result.files)
        assert (
            snapshot.translator.translate_any_scope("scanner.module_import_error", "en-US")
            == "Module import failed"
        )
        record = {
            "framework_origin": framework.__file__,
            "application_origin": importlib.import_module("server.starter_server").__file__,
            "module_count": len(snapshot.modules),
            "scan_file_count": len(snapshot.scan_result.files),
            "error_code_count": len(snapshot.error_codes.get_all()),
            "imported_modules": imported,
            "sys_path": sys.path,
        }
    assert app.state.bootstrap.definitions is None
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wheel verified: {len(imported)} modules, {record['error_code_count']} error codes, resource translation and application cleanup passed"
    )


if __name__ == "__main__":
    main()
