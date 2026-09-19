import json
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from framework.starter_config.config.config_file_settings import ConfigFileSettings
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum


class ConfigSettings(BaseModel):
    """模块配置的部署策略，默认值统一来自 application.yaml。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    models: dict[str, dict[str, object]]
    source_order: tuple[ConfigSourceEnum, ...]
    files: tuple[ConfigFileSettings, ...]
    reload_enabled: bool
    max_source_bytes: Annotated[int, Field(gt=0)]
    max_source_items: Annotated[int, Field(gt=0)]

    @field_validator("max_source_bytes", "max_source_items", mode="before")
    @classmethod
    def reject_boolean_limit(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("配置容量不能是布尔值")
        return value

    @field_validator("source_order", "files", mode="before")
    @classmethod
    def parse_json(cls, value: object) -> object:
        """环境变量中的集合使用 JSON，字段模型随后检查具体形状。"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("集合配置必须使用 JSON") from None
        return value

    @field_validator("source_order")
    @classmethod
    def unique_sources(cls, value: tuple[ConfigSourceEnum, ...]) -> tuple[ConfigSourceEnum, ...]:
        if len(value) != len(set(value)):
            raise ValueError("配置源顺序不能包含重复项")
        return value
