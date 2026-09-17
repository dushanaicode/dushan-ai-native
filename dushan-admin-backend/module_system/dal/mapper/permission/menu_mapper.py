from __future__ import annotations

from sqlalchemy import func, select

from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.permission.vo.menu.menu_list_req_vo import MenuListReqVO
from module_system.dal.dataobject.permission.menu_do import MenuDO


@mapper()
class MenuMapper(BaseMapper[MenuDO]):
    def __init__(self):
        super().__init__(MenuDO)

    async def select_by_parent_id_and_name(self, parent_id: int, name: str) -> MenuDO | None:
        stmt = select(MenuDO).where(MenuDO.parent_id == parent_id, MenuDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_count_by_parent_id(self, parent_id: int) -> int:
        stmt = select(func.count()).select_from(MenuDO).where(MenuDO.parent_id == parent_id)
        result = await self.read(stmt)
        return result.scalar_one()

    async def select_list_by_req(self, req_vo: MenuListReqVO | None = None) -> list[MenuDO]:
        stmt = select(MenuDO)
        if req_vo is not None:
            if req_vo.name:
                escaped = StrUtils.escape_like(req_vo.name)
                stmt = stmt.where(MenuDO.name.ilike(f"%{escaped}%"))
            if req_vo.status is not None:
                stmt = stmt.where(MenuDO.status == req_vo.status)
        stmt = stmt.order_by(MenuDO.id.desc())
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_permission(self, permission: str) -> list[MenuDO]:
        stmt = select(MenuDO).where(MenuDO.permission == permission)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_batch_ids(self, ids: set[int]) -> list[MenuDO]:
        stmt = select(MenuDO).where(MenuDO.id.in_(ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_permissions(self, permissions: set[str]) -> list[MenuDO]:
        """批量按权限码查菜单"""
        if not permissions:
            return []
        stmt = select(MenuDO).where(MenuDO.permission.in_(permissions))
        result = await self.read(stmt)
        return list(result.scalars().all())
