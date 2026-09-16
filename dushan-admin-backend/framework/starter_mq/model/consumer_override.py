from pydantic import BaseModel, ConfigDict, Field


class ConsumerOverride(BaseModel):
    """部署覆盖仅允许启停、并发和预取，不改变消费业务语义。"""

    model_config = ConfigDict(frozen=True, extra="forbid")
    enabled: bool | None
    concurrency: int | None = Field(strict=True, ge=1)
    prefetch: int | None = Field(strict=True, ge=1)
