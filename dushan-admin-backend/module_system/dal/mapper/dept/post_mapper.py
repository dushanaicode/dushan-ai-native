from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.dept.vo.post.post_page_req_vo import PostPageReqVO
from module_system.dal.dataobject.dept.post_do import PostDO


@mapper()
class PostMapper(BaseMapper[PostDO]):
    def __init__(self):
        super().__init__(PostDO)

    async def select_batch_ids(self, ids: Collection[int]) -> list[PostDO]:
        stmt = select(PostDO).where(PostDO.id.in_(ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_filtered_list(
        self, ids: Collection[int] | None = None, statuses: Collection[int] | None = None
    ) -> list[PostDO]:
        stmt = select(PostDO)
        if ids:
            stmt = stmt.where(PostDO.id.in_(ids))
        if statuses:
            stmt = stmt.where(PostDO.status.in_(statuses))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_page(self, req_vo: PostPageReqVO) -> PageResult[PostDO]:
        stmt = select(PostDO)
        if req_vo.code:
            escaped_code = StrUtils.escape_like(req_vo.code)
            stmt = stmt.where(PostDO.code.ilike(f"%{escaped_code}%", escape="\\"))
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(PostDO.name.ilike(f"%{escaped}%", escape="\\"))
        if req_vo.status is not None:
            stmt = stmt.where(PostDO.status == req_vo.status)
        if req_vo.create_time is not None:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(PostDO.create_time.between(start_time, end_time))
        stmt = stmt.order_by(PostDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_name(self, name: str) -> PostDO | None:
        stmt = select(PostDO).where(PostDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list_by_names(self, names: Collection[str]) -> list[PostDO]:
        """批量精确查询岗位名称，不附加状态筛选。"""
        return await self.select_list(PostDO.name.in_(names))

    async def select_by_code(self, code: str) -> PostDO | None:
        stmt = select(PostDO).where(PostDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
