from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UvicornSettings(BaseModel):
    """Uvicorn 的进程数和日志级别。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    workers: int = Field(default=1, ge=1)
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = "info"
