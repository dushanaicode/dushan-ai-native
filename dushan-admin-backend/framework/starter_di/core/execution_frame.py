from dataclasses import dataclass, field

from framework.starter_di.core.execution_owner import ExecutionOwner


@dataclass(slots=True)
class ExecutionFrame:
    """记录执行所有者与有效区间，解析路径按所有者隔离。"""

    value: object
    owner: ExecutionOwner = field(default_factory=ExecutionOwner.current)
    active: bool = True

    @property
    def is_current(self) -> bool:
        return self.active and self.owner == ExecutionOwner.current()
