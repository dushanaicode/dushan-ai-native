import json
from datetime import datetime, timezone
from uuid import uuid4

from framework.common.exception import ServiceException
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_job.public import (
    JobService as NativeJobService,
)
from framework.starter_tenant.public import (
    TenantContext,
)
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.dal.mapper.job.job_mapper import JobMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.job.job_definition_store import JobDefinitionStore
from module_infra.service.job.job_service import JobService


@service(interface=JobService)
class JobServiceImpl(JobService):
    mapper: JobMapper = Inject()
    database: SessionProvider = Inject()
    native: NativeJobService = Inject()
    tenant: TenantContext = Inject()

    def _row(self, request, identifier, status):
        values = request.model_dump(exclude={"id"}, by_alias=False)
        parameter = values["handler_param"]
        parsed = {} if parameter is None or parameter == "" else json.loads(parameter)
        if not isinstance(parsed, dict):
            raise ValueError("任务参数必须是 JSON 对象")
        return JobDO(
            id=identifier,
            **values,
            status=status,
            parameters=parsed,
            revision=uuid4().hex,
            effective_at=datetime.now(timezone.utc).replace(tzinfo=None),
            tenant_id=self.tenant.get_required_tenant_id(),
            fan_out=False,
            max_instances=1,
            timeout_seconds=300.0
            if request.monitor_timeout is None
            else request.monitor_timeout / 1000,
            retry_backoff=1.0,
            stop_after_failure=False,
        )

    @transactional
    async def create_job(self, request):
        if await self.mapper.select_by_handler_name(request.handler_name) is not None:
            raise ServiceException(ErrorCodeConstants.JOB_HANDLER_EXISTS)
        row = self._row(request, self.database.next_id(), 1)
        definition = JobDefinitionStore.definition(row)
        await self.mapper.insert(row)
        await self.native.save(definition)
        return row.id

    @transactional
    async def update_job(self, request):
        old = await self._require(request.id)
        if old.status != 1:
            raise ServiceException(ErrorCodeConstants.JOB_UPDATE_ONLY_NORMAL_STATUS)
        row = self._row(request, old.id, old.status)
        await self.native.save(JobDefinitionStore.definition(row))
        await self.mapper.update_by_id(
            JobDO(
                id=row.id,
                name=row.name,
                handler_param=row.handler_param,
                monitor_timeout=row.monitor_timeout,
            )
        )

    async def update_job_status(self, job_id, status):
        if status not in {1, 2}:
            raise ServiceException(ErrorCodeConstants.JOB_CHANGE_STATUS_INVALID)
        row = await self._require(job_id)
        if row.status == status:
            raise ServiceException(ErrorCodeConstants.JOB_CHANGE_STATUS_EQUALS)
        definition = JobDefinitionStore.definition(row).model_copy(
            update={
                "enabled": status == 1,
                "revision": uuid4().hex,
                "effective_at": datetime.now(timezone.utc),
            }
        )
        await self.native.save(definition)

    async def trigger_job(self, job_id):
        return await self.native.trigger(str(job_id))

    async def trigger_job_by_handler(self, handler_name, handler_param):
        row = await self.mapper.select_by_handler_name(handler_name)
        if row is None:
            raise ServiceException(ErrorCodeConstants.JOB_NOT_EXISTS)
        if handler_param != row.handler_param:
            raise ValueError("手动触发使用已保存参数；修改参数需更新任务定义")
        return await self.trigger_job(row.id)

    async def delete_job(self, id):
        await self._require(id)
        await self.native.delete(str(id))

    @transactional
    async def delete_job_batch(self, ids):
        for identifier in ids:
            await self.delete_job(identifier)
        return len(ids)

    async def sync_job(self):
        await self.native.synchronize()

    async def get_job(self, job_id):
        return await self.mapper.select_by_id(job_id)

    async def get_job_page(self, request):
        return await self.mapper.select_page(request)

    async def _require(self, identifier):
        row = await self.get_job(identifier)
        if row is None:
            raise ServiceException(ErrorCodeConstants.JOB_NOT_EXISTS)
        return row
