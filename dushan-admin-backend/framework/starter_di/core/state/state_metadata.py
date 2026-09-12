from dataclasses import dataclass
from typing import Any

from framework.starter_di.core.state.state_key import StateKey


@dataclass(frozen=True, slots=True)
class StateMetadata:
    """运行状态的不可变登记信息，状态实例本身仍由其资源所有者管理。"""

    key: StateKey[Any]
    instance: Any
    created_at: float
    updated_at: float
