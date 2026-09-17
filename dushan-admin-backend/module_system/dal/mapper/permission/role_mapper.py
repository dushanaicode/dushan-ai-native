from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.permission.vo.role.role_page_req_vo import RolePageReqVO
from module_system.dal.dataobject.permission.role_do import RoleDO


@mapper()
class RoleMapper(BaseMapper[RoleDO]):
    def __init__(self):
        super().__init__(RoleDO)

    async def select_page(self, req_vo: RolePageReqVO) -> PageResult[RoleDO]:
        stmt = select(RoleDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(RoleDO.name.ilike(f"%{escaped}%"))
        if req_vo.code:
            escaped_code = StrUtils.escape_like(req_vo.code)
            stmt = stmt.where(RoleDO.code.ilike(f"%{escaped_code}%"))
        if req_vo.status is not None:
            stmt = stmt.where(RoleDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                RoleDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(RoleDO.sort.asc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_name(self, name: str) -> RoleDO | None:
        stmt = select(RoleDO).where(RoleDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_code(self, code: str) -> RoleDO | None:
        stmt = select(RoleDO).where(RoleDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list_by_status(self, statuses: Collection[int]) -> list[RoleDO]:
        stmt = select(RoleDO)
        if statuses:
            stmt = stmt.where(RoleDO.status.in_(statuses))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_batch_ids(self, ids: Collection[int]) -> list[RoleDO]:
        stmt = select(RoleDO).where(RoleDO.id.in_(ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list(self) -> list[RoleDO]:
        stmt = select(RoleDO)
        result = await self.read(stmt)
        return list(result.scalars().all())
