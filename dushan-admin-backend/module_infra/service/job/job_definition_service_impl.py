from datetime import timezone
from typing import override

from sqlalchemy import select

from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.convert.job.job_convert import JobConvert
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.dal.mapper.job.job_mapper import JobMapper
from module_infra.service.job.job_definition_service import JobDefinitionService


@service(interface=JobDefinitionService)
class JobDefinitionServiceImpl(JobDefinitionService):
    """以任务表保存调度定义，供 Job 运行时读取与同步。"""

    mapper: JobMapper = Inject()

    @override
    async def list_definitions(self):
        rows = (await self.mapper.read_from_primary(select(JobDO))).scalars().all()
        return tuple((JobConvert.to_job_definition(row) for row in rows))

    @override
    async def get_definition(self, job_id):
        row = (
            await self.mapper.read_from_primary(select(JobDO).where(JobDO.id == int(job_id)))
        ).scalar_one_or_none()
        return None if row is None else JobConvert.to_job_definition(row)

    @override
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
            stored = await self.mapper.update_by_id(JobDO(**values))
            # 全局控制记录的执行目标可切换，不是租户数据的归属变更。
            stored.tenant_id = definition.tenant_id

    @override
    async def delete_definition(self, job_id):
        await self.mapper.delete_by_id(int(job_id))

    @override
    async def stop_definition(self, job_id, revision):
        await self.mapper.update_by_condition(
            {"status": 2}, JobDO.id == int(job_id), JobDO.revision == revision
        )
