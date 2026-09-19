import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import ClassVar, Mapping

from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum


@dataclass(frozen=True, slots=True)
class ConfigModelMetadata:
    """配置名称、环境前缀和来源策略；字段键是明确的点分路径。"""

    ATTRIBUTE: ClassVar[str] = "__config_metadata__"
    name: str
    env_prefix: str
    sources: tuple[ConfigSourceEnum, ...] | None = None
    field_sources: Mapping[str, tuple[ConfigSourceEnum, ...]] = field(default_factory=dict)
    field_keys: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.name):
            raise ValueError("配置模型名称必须是小写 snake_case")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*_", self.env_prefix):
            raise ValueError("配置环境前缀必须为大写名称并以 _ 结尾")
        for order in (self.sources, *self.field_sources.values()):
            if order is not None and (
                not isinstance(order, tuple)
                or any(not isinstance(item, ConfigSourceEnum) for item in order)
                or len(order) != len(set(order))
            ):
                raise TypeError("配置源策略必须是无重复的 ConfigSourceEnum 元组")
        if any(
            not key or any(not part.isidentifier() for part in key.split("."))
            for key in self.field_keys.values()
        ):
            raise ValueError("字段映射必须是明确的点分配置键")
        object.__setattr__(self, "field_sources", MappingProxyType(dict(self.field_sources)))
        object.__setattr__(self, "field_keys", MappingProxyType(dict(self.field_keys)))
