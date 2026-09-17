import json

from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.inject import Inject
from framework.starter_job.decorators.job import job
from framework.starter_job.handler.job_handler import JobHandler
from module_infra.job.infra_job_parameters import InfraJobParameters


@job(
    key="infra.database.health",
    parameters=InfraJobParameters,
    source="module_infra",
    capability="infra.database.observe",
)
class DatabaseHealthJob(JobHandler):
    database: SessionProvider = Inject()

    async def execute(self, parameters, context):
        return json.dumps(
            {
                "health": await self.database.check_health(),
                "replication": await self.database.check_replication(),
            },
            ensure_ascii=False,
        )
