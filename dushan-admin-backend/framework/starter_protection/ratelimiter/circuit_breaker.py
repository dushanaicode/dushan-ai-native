from time import monotonic


class CircuitBreaker:
    """应用事件循环内的单探针熔断；代号隔离打开前仍在途的旧结果。"""

    def __init__(self, threshold: int, reset_seconds: float) -> None:
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self.failures = 0
        self.generation = 0
        self.open_until = 0.0
        self.probing = False

    def permit(self) -> int | None:
        if self.probing:
            return None
        if self.open_until:
            if monotonic() < self.open_until:
                return None
            self.probing = True
        return self.generation

    def success(self, ticket: int) -> None:
        if ticket == self.generation:
            self.failures = 0
            self.open_until = 0.0
            self.probing = False

    def failure(self, ticket: int) -> None:
        if ticket != self.generation:
            return
        self.failures += 1
        if self.probing or self.failures >= self.threshold:
            self.generation += 1
            self.open_until = monotonic() + self.reset_seconds
            self.probing = False

    def abandon(self, ticket: int) -> None:
        if ticket == self.generation and self.probing:
            self.generation += 1
            self.open_until = monotonic() + self.reset_seconds
            self.probing = False
