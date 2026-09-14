import math
from dataclasses import dataclass
from typing import Literal

from framework.starter_protection.ratelimiter.rate_reservation import RateReservation


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    status: Literal["acquired", "rejected", "disabled", "degraded"]
    retry_after_ms: int = 0
    reservation: RateReservation | None = None

    @property
    def allowed(self) -> bool:
        return self.status != "rejected"

    @property
    def retry_after(self) -> int:
        return math.ceil(self.retry_after_ms / 1000)
