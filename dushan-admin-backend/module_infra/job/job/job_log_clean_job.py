from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobHandler,
    job,
)
from module_infra.job.infra_job_parameters import InfraJobParameters
from module_infra.service.job.job_log_service import JobLogService


@job(
    key="infra.job.log.clean",
    parameters=InfraJobParameters,
    source="module_infra",
    capability="infra.job.log.clean",
)
class JobLogCleanJob(JobHandler):
    service: JobLogService = Inject()

    async def execute(self, parameters: InfraJobParameters, context):
        """沿用调度器的租户身份清理任务日志与台账。"""
        count = await self.service.clean_job_log(parameters.retain_days, parameters.batch_size)
        return f"清理任务日志与逐租户台账 {count} 条"
