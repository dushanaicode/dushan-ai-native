from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_infra.controller.admin.job.vo.log.job_log_page_req_vo import JobLogPageReqVO
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.dal.dataobject.job.job_log_do import JobLogDO
from module_infra.dal.mapper.job.job_mapper import JobMapper


@mapper()
class JobLogMapper(BaseMapper[JobLogDO]):
    def __init__(self):
        super().__init__(JobLogDO)

    async def select_visible_by_id(
        self, log_id: int, *, tenant_id: str, include_global: bool
    ) -> JobLogDO | None:
        stmt = (
            select(JobLogDO)
            .join(JobDO, JobDO.id == JobLogDO.job_id)
            .where(
                JobLogDO.id == log_id,
                JobLogDO.deleted.is_(False),
                JobMapper.tenant_scope(tenant_id, include_global=include_global),
            )
        )
        # 任务软删除后仍按原归属读取历史日志，日志本身的软删除继续生效。
        with self.session_provider.options(include_deleted=True):
            return (await self.read(stmt)).scalar_one_or_none()

    async def select_page(
        self, req_vo: JobLogPageReqVO, *, tenant_id: str, include_global: bool
    ) -> PageResult[JobLogDO]:
        """分页查询任务日志"""
        stmt = (
            select(JobLogDO)
            .join(JobDO, JobDO.id == JobLogDO.job_id)
            .where(
                JobLogDO.deleted.is_(False),
                JobMapper.tenant_scope(tenant_id, include_global=include_global),
            )
        )
        if req_vo.job_id is not None:
            stmt = stmt.where(JobLogDO.job_id == req_vo.job_id)
        if req_vo.handler_name:
            escaped = StrUtils.escape_like(req_vo.handler_name)
            stmt = stmt.where(JobLogDO.handler_name.ilike(f"%{escaped}%", escape="\\"))
        if req_vo.begin_time:
            stmt = stmt.where(JobLogDO.begin_time >= req_vo.begin_time)
        if req_vo.end_time:
            stmt = stmt.where(JobLogDO.end_time <= req_vo.end_time)
        if req_vo.status is not None:
            stmt = stmt.where(JobLogDO.status == req_vo.status)
        stmt = stmt.order_by(JobLogDO.id.desc())
        with self.session_provider.options(include_deleted=True):
            return await self.paginate_query(stmt, req_vo)

    async def delete_by_create_time_lt(self, create_time: datetime, limit: int) -> int:
        """按每批上限清理到期任务日志，返回累计条数。"""
        return await self.purge_in_batches_by_condition(
            JobLogDO.create_time < create_time, limit=limit
        )
