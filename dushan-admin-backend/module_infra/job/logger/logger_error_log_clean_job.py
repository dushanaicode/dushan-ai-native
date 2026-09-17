from framework.starter_di.decorators.inject import Inject
from framework.starter_job.decorators.job import job
from framework.starter_job.handler.job_handler import JobHandler
from module_infra.job.infra_job_parameters import InfraJobParameters
from module_infra.service.logger.api_error_log_service import ApiErrorLogService
from module_system.api.auth.workload_api import WorkloadApi


@job(
    key="infra.log.error.clean",
    parameters=InfraJobParameters,
    source="module_infra",
    capability="infra.log.error.clean",
)
class LoggerErrorLogCleanJob(JobHandler):
    service: ApiErrorLogService = Inject()
    workloads: WorkloadApi = Inject()

    async def execute(self, parameters: InfraJobParameters, context):
        async with self.workloads.scope("infra.log.error.clean", context.tenant_id):
            count = await self.service.clean_error_log(
                parameters.retain_days if parameters.retain_days is not None else 14,
                parameters.batch_size,
            )
            return f"清理日志 {count} 条"
