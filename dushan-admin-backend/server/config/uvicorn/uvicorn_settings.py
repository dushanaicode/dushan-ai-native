"""Uvicorn 运行参数。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UvicornSettings(BaseModel):
    """生产进程数量和服务器日志级别。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    workers: int = Field(default=1, ge=1)
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = "info"
