from datetime import datetime
from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_job.public import (
    JobRequest,
    JobRequestProvider,
    JobState,
)
from module_infra.service.job.job_request_service import JobRequestService


@service(interface=JobRequestProvider)
class JobRequestProviderAdapter(JobRequestProvider):
    store: JobRequestService = Inject()

    @override
    async def submit(self, request: JobRequest, *, pending_limit: int) -> bool:
        return await self.store.submit(request, pending_limit=pending_limit)

    @override
    async def checkpoint(self, job_id: str) -> datetime | None:
        return await self.store.checkpoint(job_id)

    @override
    async def claim(
        self, owner: str, *, exclude_jobs: frozenset[str], now: datetime
    ) -> JobRequest | None:
        return await self.store.claim(owner, exclude_jobs=exclude_jobs, now=now)

    @override
    async def finish(self, request_id: str, owner: str, state: JobState) -> None:
        return await self.store.finish(request_id, owner, state)

    @override
    async def retry(self, request: JobRequest, owner: str) -> None:
        return await self.store.retry(request, owner)

    @override
    async def notify_changed(self) -> None:
        return await self.store.notify_changed()

    @override
    async def consume_changes(self) -> bool:
        return await self.store.consume_changes()
