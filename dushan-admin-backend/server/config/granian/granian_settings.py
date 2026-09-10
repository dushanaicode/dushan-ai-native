from pydantic import BaseModel, ConfigDict, Field


class GranianSettings(BaseModel):
    """Granian 的进程数和线程数。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    workers: int = Field(default=1, ge=1)
    threads: int = Field(default=1, ge=1)
