"""从安装的两个 wheel 验证配置、扫描、DI 和 FastAPI 的实际消费链。"""

import importlib
import json
import sys
from pathlib import Path


def main():
    installation, dependencies, application_root, output = map(Path, sys.argv[1:])
    sys.path[:0] = [str(installation), str(application_root)]
    sys.path.append(str(dependencies))

    from fastapi import Depends
    from fastapi.testclient import TestClient
    from foundation_probe.probe_interface import ProbeInterface
    from foundation_probe.probe_role import ProbeRole
    from foundation_probe.probe_settings import ProbeSettings

    import framework
    from framework.starter_di.context.get_bean import get_bean
    from framework.starter_di.decorators.di_dependency import DiDependency
    from framework.starter_di.enums.container_state_enum import ContainerStateEnum
    from server.starter_server import create_app

    imported = []
    for package in ("framework", "foundation_probe"):
        for path in sorted((installation / package).rglob("*.py")):
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
            "PROBE_VALUES": '["installed"]',
        },
    )

    @app.get("/probe")
    def probe(service=Depends(DiDependency(ProbeInterface))):
        assert service is get_bean(ProbeInterface)
        return {"code": 0, "message": "ok", "data": service.describe(), "error": None}

    with TestClient(app) as client:
        snapshot = app.state.bootstrap.definitions
        assert client.get("/health").status_code == 200
        assert client.get("/probe").json()["data"] == "wheel:installed"
        with snapshot.application_context.execution():
            service = snapshot.application_context.get_bean(ProbeInterface)
            assert service.started
            assert snapshot.application_context.get_bean(list[ProbeInterface]) == [service]
            assert snapshot.application_context.container.get_by_role(ProbeRole.PLUGIN) == (
                service,
            )

        async def task_probe():
            assert get_bean(ProbeInterface) is service
            return get_bean(ProbeInterface).describe()

        assert (
            client.portal.call(snapshot.application_context.tasks.run, task_probe)
            == "wheel:installed"
        )
        assert snapshot.configuration.get_config(ProbeSettings).values == ["installed"]
        assert (
            snapshot.configuration.get_sources(ProbeSettings)["values"] == "环境变量 PROBE_VALUES"
        )
        assert all(path.is_relative_to(installation) for path in snapshot.scan_result.files)
        assert (
            snapshot.translator.translate_any_scope("di.missing_binding", "en-US")
            == "An explicit dependency binding is missing"
        )
        record = {
            "framework_origin": framework.__file__,
            "imported_modules": imported,
            "scan_files": len(snapshot.scan_result.files),
            "error_codes": len(snapshot.error_codes.get_all()),
            "configuration_models": len(snapshot.configuration.model_classes),
            "di_bindings": snapshot.application_context.container.get_statistics()["bindings"],
            "sys_path": sys.path,
        }
    assert service.started is False
    assert snapshot.application_context.container.state is ContainerStateEnum.CLOSED
    assert app.state.bootstrap.definitions is None and app.state.application_context is None
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Installed artifacts verified: {len(imported)} modules, config/scanner/DI/providers/HTTP/cleanup passed"
    )


if __name__ == "__main__":
    main()
