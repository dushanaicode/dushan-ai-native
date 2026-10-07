from __future__ import annotations

from sqlalchemy import select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_infra.controller.admin.job.vo.job.job_page_req_vo import JobPageReqVO
from module_infra.dal.dataobject.job.job_do import JobDO


@mapper()
class JobMapper(BaseMapper[JobDO]):
    def __init__(self):
        super().__init__(JobDO)

    async def select_for_update(self, identifier: int) -> JobDO | None:
        """从主库锁定执行范围，锁由管理操作的事务持有。"""
        result = await self.execute(
            select(JobDO)
            .where(JobDO.id == identifier)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def select_by_handler_name(self, handler_name: str) -> JobDO | None:
        """全局唯一性查询；管理操作仍须按返回记录的租户校验权限。"""
        stmt = select(JobDO).where(JobDO.handler_name == handler_name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def tenant_scope(tenant_id: str, *, include_global: bool):
        """普通任务属于指定租户；仅默认租户另可见逐租户任务。"""
        scope = JobDO.tenant_id == tenant_id
        return scope | JobDO.tenant_id.is_(None) if include_global else scope

    async def select_page(
        self, req_vo: JobPageReqVO, *, tenant_id: str, include_global: bool
    ) -> PageResult[JobDO]:
        """分页查询定时任务"""
        stmt = select(JobDO).where(self.tenant_scope(tenant_id, include_global=include_global))
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(JobDO.name.ilike(f"%{escaped}%", escape="\\"))
        if req_vo.status is not None:
            stmt = stmt.where(JobDO.status == req_vo.status)
        if req_vo.handler_name:
            escaped_handler = StrUtils.escape_like(req_vo.handler_name)
            stmt = stmt.where(JobDO.handler_name.ilike(f"%{escaped_handler}%", escape="\\"))
        if req_vo.create_time is not None:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(JobDO.create_time.between(start_time, end_time))
        return await self.paginate_query(stmt, req_vo)
