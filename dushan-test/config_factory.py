from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

Settings = TypeVar("Settings", bound=BaseModel)


class ConfigFactory:
    """从产品公共 YAML 取得测试基础配置，场景差异由测试显式覆盖。"""

    @staticmethod
    def values() -> dict:
        """每次读取独立数据，测试不在代码里维护第二套产品默认值。"""
        path = Path(__file__).resolve().parents[1] / "dushan-admin-backend/application.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @classmethod
    def build(cls, model: type[Settings], section: str, **overrides) -> Settings:
        """使用 YAML 分组和本次场景参数构造真实配置模型。"""
        values = cls.values()[section]
        values.update(overrides)
        return model.model_validate(values)
