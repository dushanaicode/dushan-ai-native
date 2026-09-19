from pydantic import AwareDatetime, BaseModel, ConfigDict

from framework.starter_job.definitions.enums.job_state import JobState
from framework.starter_job.definitions.enums.job_trigger_kind import JobTriggerKind


class JobRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    request_id: str
    job_id: str
    handler_key: str
    attempt: int
    trigger: JobTriggerKind
    state: JobState
    started_at: AwareDatetime
    finished_at: AwareDatetime
    tenant_id: str | None
    summary: str
