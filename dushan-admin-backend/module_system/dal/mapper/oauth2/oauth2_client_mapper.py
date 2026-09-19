from __future__ import annotations

from sqlalchemy import select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.api.oauth2.dto.oauth2_client_dto import OAuth2ClientDTO
from module_system.controller.admin.oauth2.vo.client.oauth2_client_page_req_vo import (
    OAuth2ClientPageReqVO,
)
from module_system.dal.dataobject.oauth2.oauth2_client_do import OAuth2ClientDO


@mapper()
class OAuth2ClientMapper(BaseMapper[OAuth2ClientDO]):
    def __init__(self):
        super().__init__(OAuth2ClientDO)

    async def select_page(self, req_vo: OAuth2ClientPageReqVO) -> PageResult[OAuth2ClientDO]:
        stmt = select(OAuth2ClientDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(OAuth2ClientDO.name.ilike(f"%{escaped}%"))
        if req_vo.status is not None:
            stmt = stmt.where(OAuth2ClientDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                OAuth2ClientDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(OAuth2ClientDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_client_id(self, client_id: str) -> OAuth2ClientDO | None:
        query = select(OAuth2ClientDO).where(OAuth2ClientDO.client_id == client_id)
        result = await self.read(query)
        return result.scalar_one_or_none()

    async def select_details_dto_by_client_id(self, client_id: str) -> OAuth2ClientDTO | None:
        client = await self.select_by_client_id(client_id)
        if not client:
            return None
        return OAuth2ClientDTO(
            id=client.id,
            client_id=client.client_id,
            secret=client.secret,
            name=client.name,
            logo=client.logo,
            description=client.description,
            status=client.status,
            user_type=client.user_type,
            access_token_validity_seconds=client.access_token_validity_seconds,
            refresh_token_validity_seconds=client.refresh_token_validity_seconds,
            redirect_uris=client.redirect_uris,
            authorized_grant_types=client.authorized_grant_types,
            scopes=client.scopes,
            auto_approve_scopes=client.auto_approve_scopes,
            authorities=client.authorities,
            resource_ids=client.resource_ids,
            additional_information=client.additional_information,
        )
