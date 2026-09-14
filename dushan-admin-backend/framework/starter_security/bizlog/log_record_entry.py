from dataclasses import dataclass, field
from typing import Literal

from framework.starter_security.bizlog.log_record_operation import LogRecordOperation


@dataclass(frozen=True, slots=True)
class LogRecordEntry:
    operation: LogRecordOperation
    result: Literal["success", "failure", "cancelled"]
    duration_ms: float
    biz_no: str | None = field(repr=False)
    action: str = field(repr=False)
    extra: str | None = field(repr=False)
