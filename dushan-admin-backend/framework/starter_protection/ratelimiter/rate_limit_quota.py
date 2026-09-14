from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RateLimitQuota(BaseModel):
    """限流配额的必填字段；作为 YAML 默认配额或显式规则的共同契约。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: Literal["fixed", "sliding"]
    capacity: int = Field(strict=True, ge=1, le=1_000_000)
    window_ms: int = Field(strict=True, ge=1, le=2_592_000_000)
