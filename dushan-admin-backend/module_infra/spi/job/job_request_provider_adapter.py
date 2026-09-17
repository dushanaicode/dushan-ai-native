from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_job.spi.job_request_provider import JobRequestProvider
from module_infra.service.job.job_request_store import JobRequestStore


@service(interface=JobRequestProvider)
class JobRequestProviderAdapter(JobRequestProvider):
    store: JobRequestStore = Inject()

    async def submit(self, request, *, pending_limit):
        return await self.store.submit(request, pending_limit=pending_limit)

    async def checkpoint(self, job_id):
        return await self.store.checkpoint(job_id)

    async def claim(self, owner, *, exclude_jobs, now):
        return await self.store.claim(owner, exclude_jobs=exclude_jobs, now=now)

    async def finish(self, request_id, owner, state):
        return await self.store.finish(request_id, owner, state)

    async def retry(self, request, owner):
        return await self.store.retry(request, owner)

    async def notify_changed(self):
        return await self.store.notify_changed()

    async def consume_changes(self):
        return await self.store.consume_changes()
