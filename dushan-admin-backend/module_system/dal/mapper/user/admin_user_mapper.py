from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import and_, func, or_, select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.user.vo.user.user_page_req_vo import UserPageReqVO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO


@mapper()
class AdminUserMapper(BaseMapper[AdminUserDO]):
    def __init__(self):
        super().__init__(AdminUserDO)

    async def select_by_username(self, username: str) -> AdminUserDO | None:
        stmt = select(AdminUserDO).where(AdminUserDO.username == username)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_email(self, email: str) -> AdminUserDO | None:
        stmt = select(AdminUserDO).where(AdminUserDO.email == email)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_mobile(self, mobile: str) -> AdminUserDO | None:
        stmt = select(AdminUserDO).where(AdminUserDO.mobile == mobile)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_page(
        self,
        req_vo: UserPageReqVO,
        dept_ids: Collection[int] | None,
        user_ids: Collection[int] | None,
    ) -> PageResult[AdminUserDO]:
        stmt = select(AdminUserDO)
        if req_vo.username:
            escaped = StrUtils.escape_like(req_vo.username)
            stmt = stmt.where(AdminUserDO.username.ilike(f"%{escaped}%"))
        if req_vo.mobile:
            escaped_m = StrUtils.escape_like(req_vo.mobile)
            stmt = stmt.where(AdminUserDO.mobile.ilike(f"%{escaped_m}%"))
        if req_vo.status is not None:
            stmt = stmt.where(AdminUserDO.status == req_vo.status)
        if req_vo.create_time:
            stmt = stmt.where(
                AdminUserDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        if dept_ids:
            stmt = stmt.where(AdminUserDO.dept_id.in_(dept_ids))
        if user_ids:
            stmt = stmt.where(AdminUserDO.id.in_(user_ids))
        stmt = stmt.order_by(AdminUserDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_list_by_nickname(self, nickname: str) -> list[AdminUserDO]:
        escaped = StrUtils.escape_like(nickname)
        stmt = select(AdminUserDO).where(AdminUserDO.nickname.ilike("%" + escaped + "%"))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_by_keyword(self, keyword: str, limit: int = 20) -> list[AdminUserDO]:
        """按昵称或手机号模糊搜索"""
        escaped = StrUtils.escape_like(keyword)
        pattern = f"%{escaped}%"
        stmt = (
            select(AdminUserDO)
            .where(or_(AdminUserDO.nickname.ilike(pattern), AdminUserDO.mobile.ilike(pattern)))
            .limit(limit)
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_status(self, status: int) -> list[AdminUserDO]:
        stmt = select(AdminUserDO).where(AdminUserDO.status == status)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_dept_ids(self, dept_ids: Collection[int]) -> list[AdminUserDO]:
        stmt = select(AdminUserDO).where(AdminUserDO.dept_id.in_(dept_ids))
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_count_by_dept_id(self, dept_id: int) -> int:
        stmt = (
            select(func.count(AdminUserDO.id))
            .select_from(AdminUserDO)
            .where(AdminUserDO.dept_id == dept_id)
        )
        result = await self.read(stmt)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

    async def select_count(self, tenant_id: str | None = None) -> int:
        stmt = select(func.count(AdminUserDO.id)).select_from(AdminUserDO)
        conditions = []
        if tenant_id is not None:
            conditions.append(AdminUserDO.tenant_id == tenant_id)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        result = await self.read(stmt)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

    async def select_batch_ids(self, id_list: Collection[int]) -> list[AdminUserDO]:
        return await self.select_by_ids(id_list)

    async def select_by_ids(self, id_list: Collection[int]) -> list[AdminUserDO]:
        stmt = select(AdminUserDO).where(AdminUserDO.id.in_(id_list))
        result = await self.read(stmt)
        return list(result.scalars().all())
