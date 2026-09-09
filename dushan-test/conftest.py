"""只提供按需使用的临时配置，不自动登录或连接外部服务。"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def config_dir(tmp_path: Path):
    """每个用例在 pytest 的临时目录中生成独立配置。"""

    def create(base=None, *, dev=None, prod=None, local=None):
        values = {
            "server": {
                "env": "dev",
                "name": "渡山测试服务",
                "port": 48080,
                "debug": False,
                "reload": False,
                "docs_enabled": True,
            },
        }
        for key, value in (base or {}).items():
            if key == "server" and isinstance(value, dict):
                values["server"].update(value)
            else:
                values[key] = value
        layers = {
            "application.yaml": values,
            "application-dev.yaml": dev,
            "application-prod.yaml": prod,
            "application-local.yaml": local,
        }
        for name, content in layers.items():
            path = tmp_path / name
            if content is not None:
                path.write_text(yaml.safe_dump(content, allow_unicode=True), encoding="utf-8")
            elif path.exists():
                path.unlink()
        return tmp_path

    return create
