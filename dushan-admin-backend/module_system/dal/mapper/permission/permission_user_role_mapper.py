from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select

from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.dal.dataobject.permission.permission_user_role_do import UserRoleDO


@mapper()
class PermissionUserRoleMapper(BaseMapper[UserRoleDO]):
    def __init__(self):
        super().__init__(UserRoleDO)

    async def select_list_by_user_id(self, user_id: int) -> list[UserRoleDO]:
        stmt = select(UserRoleDO).where(UserRoleDO.user_id == user_id)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_role_ids(self, role_ids: Collection[int]) -> list[UserRoleDO]:
        stmt = select(UserRoleDO).where(UserRoleDO.role_id.in_(role_ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def delete_list_by_user_id_and_role_ids(
        self, user_id: int, role_ids: Collection[int]
    ) -> None:
        await self.soft_delete_by_condition(
            UserRoleDO.user_id == user_id, UserRoleDO.role_id.in_(role_ids)
        )

    async def delete_list_by_user_id(self, user_id: int) -> None:
        await self.soft_delete_by_condition(UserRoleDO.user_id == user_id)

    async def delete_list_by_role_id(self, role_id: int) -> None:
        await self.soft_delete_by_condition(UserRoleDO.role_id == role_id)
