from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_job.public import (
    JobRecord,
    JobRecordProvider,
)
from module_infra.service.job.job_log_service import JobLogService


@service(interface=JobRecordProvider)
class JobLogServiceProviderAdapter(JobRecordProvider):
    store: JobLogService = Inject()

    @override
    async def record(self, record: JobRecord) -> None:
        return await self.store.record(record)
