from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import override

from framework.common.datetime.core.date_utils import DateUtils
from framework.common.page.schemas.page_result import PageResult
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_job.enums.job_state import JobState
from module_infra.controller.admin.job.vo.log.log_page_req_vo import JobLogPageReqVO
from module_infra.dal.dataobject.job.job_log_do import JobLogDO
from module_infra.dal.mapper.job.job_log_mapper import JobLogMapper
from module_infra.service.job.job_log_service import JobLogService


@service(interface=JobLogService)
class JobLogServiceImpl(JobLogService):
    job_log_mapper: JobLogMapper = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def clean_job_log(self, exceed_day: int, delete_limit: int) -> int:
        count = 0
        expire_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=exceed_day)
        while True:
            delete_count = await self.job_log_mapper.delete_by_create_time_lt(
                expire_date, delete_limit
            )
            count += delete_count
            if delete_count < delete_limit:
                break
        return count

    @override
    async def get_job_log(self, id: int) -> JobLogDO | None:
        return await self.job_log_mapper.select_by_id(id)

    @override
    async def get_job_log_page(self, page_req_vo: JobLogPageReqVO) -> PageResult[JobLogDO]:
        return await self.job_log_mapper.select_page(page_req_vo)

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
