from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobHandler,
    job,
)
from module_infra.job.logger.logger_access_log_clean_parameters import (
    LoggerAccessLogCleanParameters,
)
from module_infra.service.logger.api_access_log_service import ApiAccessLogService


@job(
    key="infra.log.access.clean",
    parameters=LoggerAccessLogCleanParameters,
    source="module_infra",
    capability="infra.log.access.clean",
)
class LoggerAccessLogCleanJob(JobHandler):
    service: ApiAccessLogService = Inject()

    async def execute(self, parameters: LoggerAccessLogCleanParameters, context):
        """使用调度器已授权的当前租户身份清理访问日志。"""
        count = await self.service.clean_access_log(parameters.retain_days, parameters.batch_size)
        return f"清理日志 {count} 条"
