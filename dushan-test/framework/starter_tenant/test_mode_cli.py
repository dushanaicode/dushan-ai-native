import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from sqlalchemy import delete


async def test_independent_mode_cli_validates_default_only(tenant_case, config_dir, tmp_path):
    case = tenant_case
    if case.options.get("permissions"):
        pytest.skip("独立部署入口不依赖数据权限")
    desired = tmp_path / "target-mode"
    desired.mkdir()
    for file in case.config_path.glob("application*.yaml"):
        shutil.copyfile(file, desired / file.name)
    target_file = desired / "application.yaml"
    values = yaml.safe_load(target_file.read_text(encoding="utf-8"))
    values["config"]["models"]["tenant"]["enabled"] = False
    target_file.write_text(yaml.safe_dump(values, allow_unicode=True), encoding="utf-8")
    root = Path.cwd()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str(case.package_path), str(root / "dushan-admin-backend"))
    )
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    async def invoke():
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-B",
            "-m",
            "framework.starter_tenant",
            "--config-dir",
            str(case.config_path),
            "--target-config-dir",
            str(desired),
            "--directory",
            case.module.__name__ + ":DirectoryProvider",
            cwd=root,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        output, error = await asyncio.wait_for(process.communicate(), 20)
        return process.returncode, output.decode(), error.decode()

    code, _, _ = await invoke()
    assert code == 1
    async with case.engine.begin() as connection:
        await connection.execute(
            delete(case.module.Directory).where(case.module.Directory.tenant_key == "2")
        )
    code, output, error = await invoke()
    assert code == 0, error
    assert json.loads(output)["enabled"] is False
