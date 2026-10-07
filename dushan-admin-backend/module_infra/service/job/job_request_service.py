from datetime import datetime
from typing import Protocol, runtime_checkable

from framework.starter_job.public import JobRequest, JobState


@runtime_checkable
class JobRequestService(Protocol):
    """持久化调度请求信箱：去重提交、领取、终态与变更提示。"""

    async def submit(self, request: JobRequest, *, pending_limit: int) -> bool: ...

    async def checkpoint(self, job_id: str) -> datetime | None: ...

    async def claim(
        self, owner: str, *, exclude_jobs: frozenset[str], now: datetime
    ) -> JobRequest | None: ...

    async def finish(self, request_id: str, owner: str, state: JobState) -> None: ...

    async def retry(self, request: JobRequest, owner: str) -> None: ...

    async def notify_changed(self) -> None: ...

    async def consume_changes(self) -> bool: ...
