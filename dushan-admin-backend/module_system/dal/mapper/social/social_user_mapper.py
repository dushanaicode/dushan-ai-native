from __future__ import annotations

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.social.vo.user.user_page_req_vo import SocialUserPageReqVO
from module_system.dal.dataobject.social.social_user_do import SocialUserDO


@mapper()
class SocialUserMapper(BaseMapper[SocialUserDO]):
    def __init__(self):
        super().__init__(SocialUserDO)

    async def select_by_type_and_code_and_state(
        self, social_type: int, code: str, state: str
    ) -> SocialUserDO | None:
        stmt = select(SocialUserDO).where(
            SocialUserDO.type == social_type, SocialUserDO.code == code, SocialUserDO.state == state
        )
        result = await self.read(stmt)
        user = result.scalar_one_or_none()
        return user

    async def select_by_type_and_openid(self, social_type: int, openid: str) -> SocialUserDO | None:
        stmt = select(SocialUserDO).where(
            SocialUserDO.type == social_type, SocialUserDO.openid == openid
        )
        result = await self.read(stmt)
        user = result.scalar_one_or_none()
        return user

    async def select_page(self, req_vo: SocialUserPageReqVO) -> PageResult[SocialUserDO]:
        stmt = select(SocialUserDO)
        if req_vo.type is not None:
            stmt = stmt.where(SocialUserDO.type == req_vo.type)
        if req_vo.nickname:
            escaped_nick = StrUtils.escape_like(req_vo.nickname)
            stmt = stmt.where(SocialUserDO.nickname.ilike(f"%{escaped_nick}%"))
        if req_vo.openid:
            escaped_oid = StrUtils.escape_like(req_vo.openid)
            stmt = stmt.where(SocialUserDO.openid.ilike(f"%{escaped_oid}%"))
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                SocialUserDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(SocialUserDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_batch_ids(self, ids: list[int]) -> list[SocialUserDO]:
        stmt = select(SocialUserDO).where(SocialUserDO.id.in_(ids))
        result = await self.read(stmt)
        return list(result.scalars().all())
