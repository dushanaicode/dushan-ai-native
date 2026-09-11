from pathlib import Path

import pytest
import yaml
from config_factory import ConfigFactory


@pytest.fixture
def config_dir(tmp_path: Path):
    """为每个测试生成一份临时配置。"""

    def create(base=None, *, dev=None, prod=None, local=None):
        values = ConfigFactory.values()
        values["server"]["name"] = "渡山测试服务"
        values["log"]["enable_file_overall"] = False
        for key, value in (base or {}).items():
            if isinstance(value, dict) and isinstance(values.get(key), dict):
                values[key].update(value)
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
