from datetime import datetime, timezone

from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobContext,
    JobHandler,
    job,
)
from module_system.job.system_job_parameters import SystemJobParameters
from module_system.service.announcement.announcement_service import (
    AnnouncementService,
)


@job(
    key="system.announcement.publish",
    parameters=SystemJobParameters,
    source="module_system",
    capability="system.announcement.publish",
)
class AnnouncementPublishJob(JobHandler):
    announcement_service: AnnouncementService = Inject()

    async def execute(self, parameters: SystemJobParameters, context: JobContext) -> str:
        """在调度器提供的租户身份内发布到期公告并标记过期公告，失败交给调度器。"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        published = await self.announcement_service.publish_due_announcements(now)
        count = await self.announcement_service.expire_announcements(now)
        return f"公告任务完成：发布 {published} 条，过期 {count} 条"
