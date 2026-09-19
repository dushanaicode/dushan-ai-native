from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobHandler,
    job,
)
from module_infra.job.infra_job_parameters import InfraJobParameters
from module_infra.service.logger.api_access_log_service import ApiAccessLogService
from module_system.api.auth.workload_api import WorkloadApi


@job(
    key="infra.log.access.clean",
    parameters=InfraJobParameters,
    source="module_infra",
    capability="infra.log.access.clean",
)
class LoggerAccessLogCleanJob(JobHandler):
    service: ApiAccessLogService = Inject()
    workloads: WorkloadApi = Inject()

    async def execute(self, parameters: InfraJobParameters, context):
        async with self.workloads.scope("infra.log.access.clean", context.tenant_id):
            count = await self.service.clean_access_log(
                parameters.retain_days if parameters.retain_days is not None else 1,
                parameters.batch_size,
            )
            return f"清理日志 {count} 条"
