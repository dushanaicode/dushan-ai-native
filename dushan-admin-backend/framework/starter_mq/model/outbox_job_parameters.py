from pydantic import BaseModel, ConfigDict, Field


class OutboxJobParameters(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    limit: int | None = Field(default=None, ge=1)
