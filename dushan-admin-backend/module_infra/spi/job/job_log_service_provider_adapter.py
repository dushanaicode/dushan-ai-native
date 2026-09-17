from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_job.spi.job_record_provider import JobRecordProvider
from module_infra.service.job.job_log_service import JobLogService


@service(interface=JobRecordProvider)
class JobLogServiceProviderAdapter(JobRecordProvider):
    store: JobLogService = Inject()

    async def record(self, record):
        return await self.store.record(record)
