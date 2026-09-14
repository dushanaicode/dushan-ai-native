from dataclasses import dataclass

from framework.starter_di.context.execution_binding import ExecutionBinding


@dataclass(slots=True, repr=False)
class LogRecordFrame:
    binding: ExecutionBinding
    active: bool = True
