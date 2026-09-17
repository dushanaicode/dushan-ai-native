from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
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

    async def select_list(
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
            stmt = stmt.where(PostDO.code.ilike(f"%{escaped_code}%"))
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(PostDO.name.ilike(f"%{escaped}%"))
        if req_vo.status is not None:
            stmt = stmt.where(PostDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                PostDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(PostDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_name(self, name: str) -> PostDO | None:
        stmt = select(PostDO).where(PostDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_code(self, code: str) -> PostDO | None:
        stmt = select(PostDO).where(PostDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
