from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobContext,
    JobHandler,
    job,
)
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
