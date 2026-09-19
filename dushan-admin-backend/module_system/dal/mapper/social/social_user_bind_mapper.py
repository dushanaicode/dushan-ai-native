from __future__ import annotations

from sqlalchemy import select

from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.dal.dataobject.social.social_user_bind_do import SocialUserBindDO


@mapper()
class SocialUserBindMapper(BaseMapper[SocialUserBindDO]):
    def __init__(self):
        super().__init__(SocialUserBindDO)

    async def delete_by_user_type_and_user_id_and_social_type(
        self, user_type: int, user_id: int, social_type: int
    ) -> None:
        await self.soft_delete_by_condition(
            SocialUserBindDO.user_type == user_type,
            SocialUserBindDO.user_id == user_id,
            SocialUserBindDO.social_type == social_type,
        )

    async def delete_by_user_type_and_social_user_id(
        self, user_type: int, social_user_id: int
    ) -> None:
        await self.soft_delete_by_condition(
            SocialUserBindDO.user_type == user_type,
            SocialUserBindDO.social_user_id == social_user_id,
        )

    async def select_by_user_type_and_social_user_id(
        self, user_type: int, social_user_id: int
    ) -> SocialUserBindDO | None:
        stmt = select(SocialUserBindDO).where(
            SocialUserBindDO.user_type == user_type,
            SocialUserBindDO.social_user_id == social_user_id,
        )
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list_by_user_id_and_user_type(
        self, user_id: int, user_type: int
    ) -> list[SocialUserBindDO]:
        stmt = select(SocialUserBindDO).where(
            SocialUserBindDO.user_id == user_id, SocialUserBindDO.user_type == user_type
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_by_user_id_and_user_type_and_social_type(
        self, user_id: int, user_type: int, social_type: int
    ) -> SocialUserBindDO | None:
        stmt = select(SocialUserBindDO).where(
            SocialUserBindDO.user_id == user_id,
            SocialUserBindDO.user_type == user_type,
            SocialUserBindDO.social_type == social_type,
        )
        result = await self.read(stmt)
        return result.scalar_one_or_none()
