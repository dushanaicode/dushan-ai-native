from dataclasses import dataclass
from datetime import datetime

from framework.starter_job.definitions.enums.job_trigger_kind import JobTriggerKind


@dataclass(frozen=True, slots=True)
class JobContext:
    job_id: str
    handler_key: str
    request_id: str
    attempt: int
    trigger: JobTriggerKind
    scheduled_at: datetime
    tenant_id: str | None
