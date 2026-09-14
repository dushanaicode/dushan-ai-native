from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IdempotencyRule(BaseModel):
    """只阻止有效期内重复执行，不缓存业务结果。滑动模式也有绝对有效期。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["fixed", "delete_on_complete", "sliding"]
    ttl_ms: int = Field(strict=True, ge=1, le=2_592_000_000)
    max_lifetime_ms: int = Field(strict=True, ge=1, le=2_592_000_000)
    failure_action: Literal["retain", "release"]

    @model_validator(mode="after")
    def validate_lifetime(self) -> "IdempotencyRule":
        if self.max_lifetime_ms < self.ttl_ms:
            raise ValueError("max_lifetime_ms 不能小于 ttl_ms")
        return self
