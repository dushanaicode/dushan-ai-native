from __future__ import annotations

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_infra.controller.admin.job.vo.job.job_page_req_vo import JobPageReqVO
from module_infra.dal.dataobject.job.job_do import JobDO


@mapper()
class JobMapper(BaseMapper[JobDO]):
    def __init__(self):
        super().__init__(JobDO)

    async def select_list(self) -> list[JobDO]:
        """查询所有未逻辑删除的任务"""
        stmt = select(JobDO)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_by_handler_name(self, handler_name: str) -> JobDO | None:
        """根据任务处理器名称查询任务记录"""
        stmt = select(JobDO).where(JobDO.handler_name == handler_name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_page(self, req_vo: JobPageReqVO) -> PageResult[JobDO]:
        """分页查询定时任务"""
        stmt = select(JobDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(JobDO.name.ilike(f"%{escaped}%"))
        if req_vo.status is not None:
            stmt = stmt.where(JobDO.status == req_vo.status)
        if req_vo.handler_name:
            escaped_handler = StrUtils.escape_like(req_vo.handler_name)
            stmt = stmt.where(JobDO.handler_name.ilike(f"%{escaped_handler}%"))
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                JobDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        return await self.paginate_query(stmt, req_vo)
