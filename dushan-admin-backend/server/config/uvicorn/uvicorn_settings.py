from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UvicornSettings(BaseModel):
    """Uvicorn 的进程数和日志级别。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    workers: int = Field(ge=1)
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"]

    @field_validator("workers", mode="before")
    @classmethod
    def reject_boolean_workers(cls, value):
        """进程数量不接受布尔值。"""
        if isinstance(value, bool):
            raise ValueError("进程数量不能是布尔值")
        return value
