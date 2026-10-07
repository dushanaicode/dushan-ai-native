from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import override

from framework.common.dates import DateUtils
from framework.common.page import PageResult
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_job.public import (
    JobState,
)
from framework.starter_tenant.public import TenantContext, TenantSettings
from module_infra.controller.admin.job.vo.log.job_log_page_req_vo import JobLogPageReqVO
from module_infra.dal.dataobject.job.job_log_do import JobLogDO
from module_infra.dal.mapper.job.job_log_mapper import JobLogMapper
from module_infra.dal.mapper.job.tenant_job_target_mapper import TenantJobTargetMapper
from module_infra.service.job.job_log_service import JobLogService


@service(interface=JobLogService)
class JobLogServiceImpl(JobLogService):
    job_log_mapper: JobLogMapper = Inject()
    tenant_job_target_mapper: TenantJobTargetMapper = Inject()
    tenant: TenantContext = Inject()
    tenant_settings: TenantSettings = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def clean_job_log(self, exceed_day: int, delete_limit: int) -> int:
        """清理到期任务日志；默认租户另清理至多一批终结任务台账。"""
        expire_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=exceed_day)
        count = await self.job_log_mapper.delete_by_create_time_lt(expire_date, delete_limit)
        if self.tenant.get_required_tenant_id() == self.tenant_settings.default_tenant_id:
            count += await self.tenant_job_target_mapper.delete_finished_before(
                expire_date, delete_limit
            )
        return count

    @override
    async def get_job_log(self, log_id: int) -> JobLogDO | None:
        tenant_id = self.tenant.get_required_tenant_id()
        return await self.job_log_mapper.select_visible_by_id(
            log_id,
            tenant_id=tenant_id,
            include_global=tenant_id == self.tenant_settings.default_tenant_id,
        )

    @override
    async def get_job_log_page(self, page_req_vo: JobLogPageReqVO) -> PageResult[JobLogDO]:
        tenant_id = self.tenant.get_required_tenant_id()
        return await self.job_log_mapper.select_page(
            page_req_vo,
            tenant_id=tenant_id,
            include_global=tenant_id == self.tenant_settings.default_tenant_id,
        )

    async def record(self, record):
        await self.job_log_mapper.insert(
            JobLogDO(
                job_id=int(record.job_id),
                handler_name=record.handler_key,
                handler_param=None,
                request_id=record.request_id,
                execute_index=record.attempt,
                begin_time=record.started_at.astimezone(timezone.utc).replace(tzinfo=None),
                end_time=record.finished_at.astimezone(timezone.utc).replace(tzinfo=None),
                duration=int((record.finished_at - record.started_at).total_seconds() * 1000),
                status=1 if record.state is JobState.SUCCEEDED else 2,
                state=record.state.code,
                result=record.summary[:4096],
            )
        )
