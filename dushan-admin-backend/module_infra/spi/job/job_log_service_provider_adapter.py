from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_job.public import (
    JobRecordProvider,
)
from module_infra.service.job.job_log_service import JobLogService


@service(interface=JobRecordProvider)
class JobLogServiceProviderAdapter(JobRecordProvider):
    store: JobLogService = Inject()

    async def record(self, record):
        return await self.store.record(record)
