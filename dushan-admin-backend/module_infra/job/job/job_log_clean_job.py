from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobHandler,
    job,
)
from module_infra.job.infra_job_parameters import InfraJobParameters
from module_infra.service.job.job_log_service import JobLogService
from module_system.api.auth.workload_api import WorkloadApi


@job(
    key="infra.job.log.clean",
    parameters=InfraJobParameters,
    source="module_infra",
    capability="infra.job.log.clean",
)
class JobLogCleanJob(JobHandler):
    service: JobLogService = Inject()
    workloads: WorkloadApi = Inject()

    async def execute(self, parameters: InfraJobParameters, context):
        async with self.workloads.scope("infra.job.log.clean", context.tenant_id):
            count = await self.service.clean_job_log(
                parameters.retain_days if parameters.retain_days is not None else 14,
                parameters.batch_size,
            )
            return f"清理日志 {count} 条"
