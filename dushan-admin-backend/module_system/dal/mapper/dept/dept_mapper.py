from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import func, select

from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.dept.vo.dept.dept_list_req_vo import DeptListReqVO
from module_system.dal.dataobject.dept.dept_do import DeptDO


@mapper()
class DeptMapper(BaseMapper[DeptDO]):
    def __init__(self):
        super().__init__(DeptDO)

    async def select_batch_ids(self, ids: Collection[int]) -> list[DeptDO]:
        stmt = select(DeptDO).where(DeptDO.id.in_(ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_vo(self, req_vo: DeptListReqVO) -> list[DeptDO]:
        stmt = select(DeptDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(DeptDO.name.ilike(f"%{escaped}%"))
        if req_vo.status is not None:
            stmt = stmt.where(DeptDO.status == req_vo.status)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_status(self, status: int) -> list[DeptDO]:
        stmt = select(DeptDO).where(DeptDO.status == status)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_by_parent_id_and_name(self, parent_id: int, name: str) -> DeptDO | None:
        stmt = select(DeptDO).where(DeptDO.parent_id == parent_id, DeptDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_count_by_parent_id(self, parent_id: int) -> int:
        stmt = select(func.count(DeptDO.id)).where(DeptDO.parent_id == parent_id)
        result = await self.read(stmt)
        return result.scalar_one()

    async def select_list_by_parent_id(self, parent_ids: Collection[int]) -> list[DeptDO]:
        stmt = select(DeptDO).where(DeptDO.parent_id.in_(parent_ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_leader_user_id(self, leader_user_id: int) -> list[DeptDO]:
        stmt = select(DeptDO).where(DeptDO.leader_user_id == leader_user_id)
        result = await self.read(stmt)
        return list(result.scalars().all())
