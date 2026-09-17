from __future__ import annotations

from sqlalchemy import select

from framework.common.enums.status_enum import StatusEnum
from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.social.vo.client.social_client_page_req_vo import (
    SocialClientPageReqVO,
)
from module_system.dal.dataobject.social.social_client_do import SocialClientDO


@mapper()
class SocialClientMapper(BaseMapper[SocialClientDO]):
    def __init__(self):
        super().__init__(SocialClientDO)

    async def select_by_social_type_and_user_type(
        self, social_type: int, user_type: int | None
    ) -> SocialClientDO | None:
        stmt = select(SocialClientDO).where(SocialClientDO.social_type == social_type)
        if user_type is not None:
            stmt = stmt.where(SocialClientDO.user_type == user_type)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list_by_status(self) -> list[SocialClientDO]:
        stmt = select(SocialClientDO).where(SocialClientDO.status == StatusEnum.ENABLE.code)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_page(self, req_vo: SocialClientPageReqVO) -> PageResult[SocialClientDO]:
        stmt = select(SocialClientDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(SocialClientDO.name.ilike(f"%{escaped}%"))
        if req_vo.social_type is not None:
            stmt = stmt.where(SocialClientDO.social_type == req_vo.social_type)
        if req_vo.user_type is not None:
            stmt = stmt.where(SocialClientDO.user_type == req_vo.user_type)
        if req_vo.client_id:
            escaped_cid = StrUtils.escape_like(req_vo.client_id)
            stmt = stmt.where(SocialClientDO.client_id.ilike(f"%{escaped_cid}%"))
        if req_vo.status is not None:
            stmt = stmt.where(SocialClientDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                SocialClientDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(SocialClientDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def update(self, client: SocialClientDO) -> None:
        await self.update_by_id(client)
