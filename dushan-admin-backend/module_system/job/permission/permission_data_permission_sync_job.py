from framework.starter_di.decorators.inject import Inject
from framework.starter_job.decorators.job import job
from framework.starter_job.handler.job_handler import JobHandler
from framework.starter_job.model.job_context import JobContext
from module_system.job.system_job_parameters import SystemJobParameters
from module_system.service.permission.permission_cache_service import (
    PermissionCacheService,
)


@job(
    key="system.permission.sync",
    parameters=SystemJobParameters,
    source="module_system",
    capability="system.permission.sync",
)
class PermissionDataPermissionSyncJob(JobHandler):
    publisher: PermissionCacheService = Inject()

    async def execute(self, parameters: SystemJobParameters, context: JobContext) -> str:
        await self.publisher.invalidate_all()
        return "数据权限同步任务完成"
