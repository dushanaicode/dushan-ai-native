from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_infra.controller.admin.job.vo.log.log_page_req_vo import JobLogPageReqVO
from module_infra.dal.dataobject.job.job_log_do import JobLogDO


@mapper()
class JobLogMapper(BaseMapper[JobLogDO]):
    def __init__(self):
        super().__init__(JobLogDO)

    async def select_list(self) -> list[JobLogDO]:
        """查询所有任务日志"""
        stmt = select(JobLogDO)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_page(self, req_vo: JobLogPageReqVO) -> PageResult[JobLogDO]:
        """分页查询任务日志"""
        stmt = select(JobLogDO)
        if req_vo.job_id is not None:
            stmt = stmt.where(JobLogDO.job_id == req_vo.job_id)
        if req_vo.handler_name:
            escaped = StrUtils.escape_like(req_vo.handler_name)
            stmt = stmt.where(JobLogDO.handler_name.ilike(f"%{escaped}%"))
        if req_vo.begin_time:
            stmt = stmt.where(JobLogDO.begin_time >= req_vo.begin_time)
        if req_vo.end_time:
            stmt = stmt.where(JobLogDO.end_time <= req_vo.end_time)
        if req_vo.status is not None:
            stmt = stmt.where(JobLogDO.status == req_vo.status)
        stmt = stmt.order_by(JobLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def delete_by_create_time_lt(self, create_time: datetime, limit: int) -> int:
        return await self.purge_limited_by_condition(
            JobLogDO.create_time < create_time, limit=limit
        )
