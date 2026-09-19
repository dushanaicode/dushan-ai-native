from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from framework.starter_job.definitions.enums.job_trigger_kind import JobTriggerKind
from framework.starter_job.model.job_definition import JobDefinition


class JobRequest(BaseModel):
    """跨进程执行请求；重试沿用 request_id，重新验证当前定义与工作负载授权。"""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, hide_input_in_errors=True)
    request_id: str = Field(min_length=1, max_length=128)
    definition: JobDefinition
    trigger: JobTriggerKind
    scheduled_at: AwareDatetime
    ready_at: AwareDatetime
    attempt: int = Field(strict=True, ge=1)

    @model_validator(mode="after")
    def validate_ready_time(self):
        if self.ready_at < self.scheduled_at:
            raise ValueError("执行请求不能早于应触发时间到期")
        return self
