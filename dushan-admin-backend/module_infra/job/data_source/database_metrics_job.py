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
    key="infra.database.metrics",
    parameters=InfraObservationParameters,
    source="module_infra",
    capability="infra.database.observe",
)
class DatabaseMetricsJob(JobHandler):
    database: SessionProvider = Inject()

    async def execute(self, parameters: InfraObservationParameters, context):
        """采集数据库连接池与监控指标。"""
        return self.database.get_metrics()
