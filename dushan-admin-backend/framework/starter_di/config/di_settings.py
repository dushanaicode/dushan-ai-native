from pydantic import BaseModel, ConfigDict, Field, field_validator

from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum


class DiSettings(BaseModel):
    """DI 部署策略，省略字段不会获得代码默认值。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool
    default_scope: ComponentScopeEnum
    hook_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    lookup_enabled: bool
    automatic_context_binding: bool
    drain_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    metrics_enabled: bool
    task_error_limit: int = Field(gt=0, le=10_000)

    @field_validator(
        "hook_timeout_seconds", "drain_timeout_seconds", "task_error_limit", mode="before"
    )
    @classmethod
    def reject_boolean_number(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("生命周期超时和保留上限不能是布尔值")
        return value
