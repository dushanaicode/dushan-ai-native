from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpressionOptions(BaseModel):
    """声明表达式执行开关与资源上限，所有默认值由公共 YAML 提供。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    enabled: bool
    max_length: int = Field(gt=0)
    max_context_bytes: int = Field(gt=0)
    max_output_bytes: int = Field(gt=0)
    max_depth: int = Field(gt=0)

    @field_validator(
        "max_length", "max_context_bytes", "max_output_bytes", "max_depth", mode="before"
    )
    @classmethod
    def reject_boolean_limits(cls, value: object) -> object:
        """拒绝把布尔值作为容量限制。"""
        if isinstance(value, bool):
            raise ValueError("表达式容量限制不能是布尔值")
        return value
