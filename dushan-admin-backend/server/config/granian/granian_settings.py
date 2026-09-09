"""Granian 运行参数。"""

from pydantic import BaseModel, ConfigDict, Field


class GranianSettings(BaseModel):
    """生产进程和运行线程数量。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    workers: int = Field(default=1, ge=1)
    threads: int = Field(default=1, ge=1)
