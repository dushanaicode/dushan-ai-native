from framework.starter_job.decorators.job import job
from framework.starter_job.handler.job_handler import JobHandler
from framework.starter_mq.core.outbox_service import OutboxService
from framework.starter_mq.model.outbox_job_parameters import OutboxJobParameters


@job(
    key="mq.outbox.dispatch",
    parameters=OutboxJobParameters,
    source="mq.outbox",
    capability="mq:dispatch",
)
class OutboxJob(JobHandler):
    """由任务定义 SPI 启用公共计划；不绕过 Job owner 或自建后台定时器。"""

    def __init__(self, outbox: OutboxService):
        self.outbox = outbox

    async def execute(self, parameters, context):
        result = await self.outbox.dispatch(limit=parameters.limit)
        result["cleaned"] = await self.outbox.cleanup()
        return result
