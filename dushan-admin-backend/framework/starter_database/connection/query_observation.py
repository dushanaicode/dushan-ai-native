from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QueryObservation:
    """单次游标执行的安全事件；不包含 SQL 原文、参数或驱动异常。"""

    source: str
    operation: str
    template: str | None
    fingerprint: str | None
    elapsed_ms: float
    success: bool
