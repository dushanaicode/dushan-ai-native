from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select

from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.dal.dataobject.permission.role_menu_do import RoleMenuDO


@mapper()
class RoleMenuMapper(BaseMapper[RoleMenuDO]):
    def __init__(self):
        super().__init__(RoleMenuDO)

    async def select_list_by_role_id(self, role_id: int) -> list[RoleMenuDO]:
        stmt = select(RoleMenuDO).where(RoleMenuDO.role_id == role_id)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_role_ids(self, role_ids: Collection[int]) -> list[RoleMenuDO]:
        stmt = select(RoleMenuDO).where(RoleMenuDO.role_id.in_(role_ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_menu_id(self, menu_id: int) -> list[RoleMenuDO]:
        stmt = select(RoleMenuDO).where(RoleMenuDO.menu_id == menu_id)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def sync_menu_ids(self, role_id: int, current: set[int], wanted: set[int]) -> bool:
        """在调用方事务内按差量同步角色菜单，返回关系是否变化。"""
        if removed := current - wanted:
            await self.soft_delete_by_condition(
                RoleMenuDO.role_id == role_id, RoleMenuDO.menu_id.in_(removed)
            )
        await self.insert_batch(
            [RoleMenuDO(role_id=role_id, menu_id=menu_id) for menu_id in wanted - current]
        )
        return current != wanted

    async def delete_list_by_menu_id(self, menu_id: int) -> None:
        await self.soft_delete_by_condition(RoleMenuDO.menu_id == menu_id)

    async def delete_list_by_role_id(self, role_id: int) -> None:
        await self.soft_delete_by_condition(RoleMenuDO.role_id == role_id)
