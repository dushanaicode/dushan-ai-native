from dataclasses import dataclass
from typing import TYPE_CHECKING

from framework.starter_di.context.execution_phase_enum import ExecutionPhaseEnum

if TYPE_CHECKING:
    from framework.starter_di.context.application_context import ApplicationContext


@dataclass(eq=False, slots=True)
class ExecutionBinding:
    """完整执行区间的应用归属；父区间结束后继承的引用立即失效。"""

    application: "ApplicationContext"
    phase: ExecutionPhaseEnum
    active: bool = True
