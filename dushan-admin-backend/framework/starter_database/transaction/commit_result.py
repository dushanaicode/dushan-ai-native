from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommitResult:
    name: str
    success: bool
    error_type: str | None = None
