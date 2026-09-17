from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.future import select

from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.oauth2.vo.token.token_access_token_page_req_vo import (
    OAuth2AccessTokenPageReqVO,
)
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO


@mapper()
class OAuth2AccessTokenMapper(BaseMapper[OAuth2AccessTokenDO]):
    def __init__(self):
        super().__init__(OAuth2AccessTokenDO)

    async def select_by_digest(self, token_digest: str) -> OAuth2AccessTokenDO | None:
        stmt = select(OAuth2AccessTokenDO).where(OAuth2AccessTokenDO.token_digest == token_digest)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list_by_refresh_token_id(
        self, refresh_token_id: int
    ) -> list[OAuth2AccessTokenDO]:
        stmt = select(OAuth2AccessTokenDO).where(
            OAuth2AccessTokenDO.refresh_token_id == refresh_token_id
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_user_id(
        self, user_id: int, user_type: int
    ) -> list[OAuth2AccessTokenDO]:
        stmt = select(OAuth2AccessTokenDO).where(
            OAuth2AccessTokenDO.user_id == user_id, OAuth2AccessTokenDO.user_type == user_type
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_page(
        self, req_vo: OAuth2AccessTokenPageReqVO
    ) -> PageResult[OAuth2AccessTokenDO]:
        stmt = select(OAuth2AccessTokenDO)
        if req_vo.user_id is not None:
            stmt = stmt.where(OAuth2AccessTokenDO.user_id == req_vo.user_id)
        if req_vo.user_type is not None:
            stmt = stmt.where(OAuth2AccessTokenDO.user_type == req_vo.user_type)
        if req_vo.client_id:
            stmt = stmt.where(OAuth2AccessTokenDO.client_id == req_vo.client_id)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                OAuth2AccessTokenDO.create_time.between(
                    req_vo.create_time[0], req_vo.create_time[1]
                )
            )
        stmt = stmt.where(
            OAuth2AccessTokenDO.expires_time > datetime.now(timezone.utc).replace(tzinfo=None)
        )
        stmt = stmt.order_by(OAuth2AccessTokenDO.id.desc())
        return await self.paginate_query(stmt, req_vo)
