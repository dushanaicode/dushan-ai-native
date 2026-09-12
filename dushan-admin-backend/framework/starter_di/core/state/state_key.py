from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class StateKey(Generic[T]):
    """按明确名称和类型标识运行状态，例如 StateKey('cache.client', Client)。"""

    name: str
    value_type: type[Any] | tuple[type[Any], ...]
    description: str = field(default="", compare=False, hash=False)

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.strip():
            raise ValueError("状态名称不能为空或带首尾空白")
        types = (self.value_type,) if isinstance(self.value_type, type) else self.value_type
        if (
            not isinstance(types, tuple)
            or not types
            or any(not isinstance(value, type) for value in types)
        ):
            raise TypeError("状态值类型必须是类型或非空类型元组")
