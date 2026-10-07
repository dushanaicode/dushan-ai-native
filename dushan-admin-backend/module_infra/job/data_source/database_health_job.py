from framework.starter_database.public import (
    SessionProvider,
)
from framework.starter_di.public import (
    Inject,
)
from framework.starter_job.public import (
    JobHandler,
    job,
)
from module_infra.job.infra_observation_parameters import InfraObservationParameters


@job(
    key="infra.database.health",
    parameters=InfraObservationParameters,
    source="module_infra",
    capability="infra.database.observe",
)
class DatabaseHealthJob(JobHandler):
    database: SessionProvider = Inject()

    async def execute(self, parameters: InfraObservationParameters, context):
        """采集数据库健康状态与主从复制状态。"""
        return {
            "health": await self.database.check_health(),
            "replication": await self.database.check_replication(),
        }
