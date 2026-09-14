import math
from dataclasses import dataclass
from typing import Literal

from framework.starter_protection.idempotent.idempotency_claim import IdempotencyClaim


@dataclass(frozen=True, slots=True)
class IdempotencyResult:
    status: Literal["acquired", "duplicate", "disabled"]
    retry_after_ms: int = 0
    claim: IdempotencyClaim | None = None

    @property
    def retry_after(self) -> int:
        return math.ceil(self.retry_after_ms / 1000)
