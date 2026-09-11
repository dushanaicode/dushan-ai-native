from pydantic import BaseModel, ConfigDict, Field, field_validator


class GranianSettings(BaseModel):
    """Granian 的进程数和线程数。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    workers: int = Field(ge=1)
    threads: int = Field(ge=1)

    @field_validator("workers", "threads", mode="before")
    @classmethod
    def reject_boolean_counts(cls, value):
        """进程和线程数量不接受布尔值。"""
        if isinstance(value, bool):
            raise ValueError("进程和线程数量不能是布尔值")
        return value
