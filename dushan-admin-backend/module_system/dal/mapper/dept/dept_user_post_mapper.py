from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select, update

from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.dal.dataobject.dept.dept_user_post_do import UserPostDO


@mapper()
class DeptUserPostMapper(BaseMapper[UserPostDO]):
    def __init__(self):
        super().__init__(UserPostDO)

    async def select_list_by_user_id(self, user_id: int) -> list[UserPostDO]:
        stmt = select(UserPostDO).where(UserPostDO.user_id == user_id)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def delete_by_user_id_and_post_id(self, user_id: int, post_ids: Collection[int]) -> None:
        stmt = (
            update(UserPostDO)
            .where(
                UserPostDO.user_id == user_id,
                UserPostDO.post_id.in_(post_ids),
                UserPostDO.deleted.is_(False),
            )
            .values(deleted=True)
        )
        await self.write(stmt)

    async def select_list_by_post_ids(self, post_ids: Collection[int]) -> list[UserPostDO]:
        stmt = select(UserPostDO).where(UserPostDO.post_id.in_(post_ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def delete_by_user_id(self, user_id: int) -> None:
        stmt = (
            update(UserPostDO)
            .where(UserPostDO.user_id == user_id, UserPostDO.deleted.is_(False))
            .values(deleted=True)
        )
        await self.write(stmt)

    async def insert_batch(self, user_post_list: list[UserPostDO]) -> None:
        for user_post in user_post_list:
            await self.insert(user_post)

    async def insert_batch_by_user_id(self, user_id: int, post_ids: Collection[int]) -> None:
        """批量插入用户岗位关联"""
        for post_id in post_ids:
            await self.insert(UserPostDO(user_id=user_id, post_id=post_id))
