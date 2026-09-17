from datetime import timezone

from sqlalchemy import select

from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_job.model.job_definition import JobDefinition
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.dal.mapper.job.job_mapper import JobMapper


@service
class JobDefinitionStore:
    mapper: JobMapper = Inject()

    @staticmethod
    def definition(row):
        return JobDefinition(
            id=str(row.id),
            handler_key=row.handler_name,
            parameters=row.parameters,
            cron=row.cron_expression,
            enabled=row.status == 1,
            revision=row.revision,
            effective_at=row.effective_at.replace(tzinfo=timezone.utc),
            max_instances=row.max_instances,
            timeout_seconds=float(row.timeout_seconds),
            max_retries=row.retry_count,
            retry_seconds=row.retry_interval / 1000,
            retry_backoff=float(row.retry_backoff),
            stop_after_failure=row.stop_after_failure,
            tenant_id=row.tenant_id,
            fan_out=row.fan_out,
        )

    async def list_definitions(self):
        rows = (await self.mapper.read_from_primary(select(JobDO))).scalars().all()
        return tuple((self.definition(row) for row in rows))

    async def get_definition(self, job_id):
        row = (
            await self.mapper.read_from_primary(select(JobDO).where(JobDO.id == int(job_id)))
        ).scalar_one_or_none()
        return None if row is None else self.definition(row)

    @transactional
    async def save_definition(self, definition):
        row = await self.mapper.select_by_id(int(definition.id))
        values = dict(
            id=int(definition.id),
            handler_name=definition.handler_key,
            parameters=definition.parameters,
            cron_expression=definition.cron,
            status=1 if definition.enabled else 2,
            revision=definition.revision,
            effective_at=definition.effective_at.astimezone(timezone.utc).replace(tzinfo=None),
            max_instances=definition.max_instances,
            timeout_seconds=definition.timeout_seconds,
            retry_count=definition.max_retries,
            retry_interval=int(definition.retry_seconds * 1000),
            retry_backoff=definition.retry_backoff,
            stop_after_failure=definition.stop_after_failure,
            tenant_id=definition.tenant_id,
            fan_out=definition.fan_out,
        )
        if row is None:
            await self.mapper.insert(JobDO(name=definition.handler_key, **values))
        else:
            await self.mapper.update_by_id(JobDO(**values))

    async def delete_definition(self, job_id):
        await self.mapper.delete_by_id(int(job_id))

    async def stop_definition(self, job_id, revision):
        await self.mapper.update_by_condition(
            {"status": 2}, JobDO.id == int(job_id), JobDO.revision == revision
        )
