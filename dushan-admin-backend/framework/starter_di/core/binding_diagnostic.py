from dataclasses import dataclass

from framework.starter_di.definitions.enums.binding_outcome_enum import BindingOutcomeEnum


@dataclass(frozen=True, slots=True)
class BindingDiagnostic:
    """单个候选在本次启动装配中的结果与原因；只在启动时按候选数量记录，供排错查询。"""

    component: str
    key: str
    providers: tuple[str, ...]
    outcome: BindingOutcomeEnum
    reason: str
