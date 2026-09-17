from __future__ import annotations

from sqlalchemy import select

from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.dal.dataobject.user.admin_user_profile_do import AdminUserProfileDO


@mapper()
class AdminUserProfileMapper(BaseMapper[AdminUserProfileDO]):
    def __init__(self):
        super().__init__(AdminUserProfileDO)

    async def select_by_user_id(self, user_id: int) -> AdminUserProfileDO | None:
        stmt = select(AdminUserProfileDO).where(AdminUserProfileDO.user_id == user_id)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
