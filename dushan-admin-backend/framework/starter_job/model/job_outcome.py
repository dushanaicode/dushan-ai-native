from dataclasses import dataclass

from framework.starter_job.enums.job_state import JobState


@dataclass(frozen=True, slots=True)
class JobOutcome:
    state: JobState
    result: object = None
    error: BaseException | None = None
    observation_errors: tuple[BaseException, ...] = ()
