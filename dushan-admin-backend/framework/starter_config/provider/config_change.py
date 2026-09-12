from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfigChange:
    """配置已提交的变更通知，不携带敏感配置值。"""

    revision: int
    models: tuple[str, ...]
