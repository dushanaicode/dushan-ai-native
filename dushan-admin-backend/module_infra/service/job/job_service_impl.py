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
    TenantSettings,
)
from module_infra.convert.job.job_convert import JobConvert
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.dal.mapper.job.job_mapper import JobMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.job.job_service import JobService


@service(interface=JobService)
class JobServiceImpl(JobService):
    mapper: JobMapper = Inject()
    database: SessionProvider = Inject()
    native: NativeJobService = Inject()
    tenant: TenantContext = Inject()
    tenant_settings: TenantSettings = Inject()

    def _row(self, request, identifier, status):
        self._check_fan_out_access(request.fan_out)
        values = request.to_write_dict(
            fields={
                "name",
                "handler_name",
                "handler_param",
                "cron_expression",
                "retry_count",
                "retry_interval",
                "monitor_timeout",
                "fan_out",
            },
            exclude_unset=False,
        )
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
            tenant_id=None if request.fan_out else self.tenant.get_required_tenant_id(),
            max_instances=1,
            timeout_seconds=300.0
            if request.monitor_timeout is None
            else request.monitor_timeout / 1000,
            retry_backoff=1.0,
            stop_after_failure=False,
        )

    @transactional
    async def create_job(self, create_req_vo):
        row = self._row(create_req_vo, self.database.next_id(), 1)
        if await self.mapper.select_by_handler_name(create_req_vo.handler_name) is not None:
            raise ServiceException(ErrorCodeConstants.JOB_HANDLER_EXISTS)
        definition = JobConvert.to_job_definition(row)
        await self.mapper.insert(row)
        await self.native.save(definition)
        return row.id

    @transactional
    async def update_job(self, update_req_vo):
        old = await self._require(update_req_vo.id)
        row = self._row(update_req_vo, old.id, old.status)
        if old.status != 1:
            raise ServiceException(ErrorCodeConstants.JOB_UPDATE_ONLY_NORMAL_STATUS)
        existing = await self.mapper.select_by_handler_name(row.handler_name)
        if existing is not None and existing.id != old.id:
            raise ServiceException(ErrorCodeConstants.JOB_HANDLER_EXISTS)
        await self.native.save(JobConvert.to_job_definition(row))
        await self.mapper.update_by_id(
            JobDO(
                id=row.id,
                name=row.name,
                handler_param=row.handler_param,
                monitor_timeout=row.monitor_timeout,
            )
        )

    @transactional
    async def update_job_status(self, job_id, status):
        row = await self._require(job_id)
        if status not in {1, 2}:
            raise ServiceException(ErrorCodeConstants.JOB_CHANGE_STATUS_INVALID)
        if row.status == status:
            raise ServiceException(ErrorCodeConstants.JOB_CHANGE_STATUS_EQUALS)
        definition = JobConvert.to_job_definition(row).model_copy(
            update={
                "enabled": status == 1,
                "revision": uuid4().hex,
                "effective_at": datetime.now(timezone.utc),
            }
        )
        await self.native.save(definition)

    @transactional
    async def trigger_job(self, job_id):
        await self._require(job_id)
        return await self.native.trigger(str(job_id))

    @transactional
    async def trigger_job_by_handler(self, handler_name, handler_param):
        row = await self.mapper.select_by_handler_name(handler_name)
        if row is None:
            raise ServiceException(ErrorCodeConstants.JOB_NOT_EXISTS)
        row = await self._require(row.id)
        if handler_param != row.handler_param:
            raise ServiceException(ErrorCodeConstants.JOB_PARAMETERS_MISMATCH)
        return await self.native.trigger(str(row.id))

    @transactional
    async def delete_job(self, id):
        await self._require(id)
        await self.native.delete(str(id))

    @transactional
    async def delete_job_batch(self, ids):
        for identifier in ids:
            await self._require(identifier)
        for identifier in ids:
            await self.native.delete(str(identifier))
        return len(ids)

    async def sync_job(self):
        await self.native.synchronize()

    async def get_job(self, job_id):
        row = await self.mapper.select_by_id(job_id)
        if row is not None and not self._can_access(row):
            return None
        return row

    async def get_job_page(self, page_req_vo):
        return await self.mapper.select_page(
            page_req_vo,
            tenant_id=self.tenant.get_required_tenant_id(),
            include_global=self._is_default_tenant(),
        )

    async def _require(self, identifier: int) -> JobDO:
        row = await self.mapper.select_for_update(identifier)
        if row is None or not self._can_access(row):
            raise ServiceException(ErrorCodeConstants.JOB_NOT_EXISTS)
        return row

    def _can_access(self, row):
        if row.tenant_id is None:
            return self._is_default_tenant()
        return row.tenant_id == self.tenant.get_required_tenant_id()

    def _check_fan_out_access(self, fan_out):
        if fan_out and not self._is_default_tenant():
            raise ServiceException(ErrorCodeConstants.JOB_FAN_OUT_DEFAULT_TENANT_ONLY)

    def _is_default_tenant(self):
        return self.tenant.get_required_tenant_id() == self.tenant_settings.default_tenant_id
