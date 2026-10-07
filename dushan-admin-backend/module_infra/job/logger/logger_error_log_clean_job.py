from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobHandler,
    job,
)
from module_infra.job.infra_job_parameters import InfraJobParameters
from module_infra.service.logger.api_error_log_service import ApiErrorLogService


@job(
    key="infra.log.error.clean",
    parameters=InfraJobParameters,
    source="module_infra",
    capability="infra.log.error.clean",
)
class LoggerErrorLogCleanJob(JobHandler):
    service: ApiErrorLogService = Inject()

    async def execute(self, parameters: InfraJobParameters, context):
        """使用调度器已授权的当前租户身份清理错误日志。"""
        count = await self.service.clean_error_log(parameters.retain_days, parameters.batch_size)
        return f"清理日志 {count} 条"
