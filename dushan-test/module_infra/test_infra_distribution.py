import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


def test_wheel_contains_exact_sources_resources_and_imports(tmp_path):
    wheel_path = os.environ.get("DUSHAN_INFRA_WHEEL")
    if wheel_path is None:
        pytest.skip("单独构建 wheel 后通过 DUSHAN_INFRA_WHEEL 验证发行内容")
    source = Path(__file__).resolve().parents[2] / "dushan-admin-backend/module_infra"
    with zipfile.ZipFile(wheel_path) as wheel:
        entries = set(wheel.namelist())
        for path in source.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".json", ".jinja2"}:
                name = "module_infra/" + path.relative_to(source).as_posix()
                assert name in entries
                assert wheel.read(name) == path.read_bytes(), name
        assert "module_infra/module.toml" in entries
        assert not any("/Temp/" in path or "/__pycache__/" in path for path in entries)
    script = "import sys; sys.path.insert(0, sys.argv[1]); import module_infra; from module_infra.router import routers; from importlib.resources import files; assert sys.argv[1] in module_infra.__file__; assert files('module_infra').joinpath('module.toml').is_file(); assert len(routers) == 2"
    temp = tmp_path / "Temp/wheel-import"
    temp.mkdir(parents=True)
    environment = dict(os.environ, **{name: str(temp) for name in ("TEMP", "TMP", "TMPDIR")})
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(Path(wheel_path).resolve())],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
