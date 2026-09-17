from __future__ import annotations

from sqlalchemy import Result, select, update

from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.dal.dataobject.oauth2.oauth2_approve_do import OAuth2ApproveDO


@mapper()
class OAuth2ApproveMapper(BaseMapper[OAuth2ApproveDO]):
    def __init__(self):
        super().__init__(OAuth2ApproveDO)

    async def update(self, update_obj: OAuth2ApproveDO) -> int:
        stmt = (
            update(OAuth2ApproveDO)
            .where(
                OAuth2ApproveDO.user_id == update_obj.user_id,
                OAuth2ApproveDO.user_type == update_obj.user_type,
                OAuth2ApproveDO.client_id == update_obj.client_id,
                OAuth2ApproveDO.scope == update_obj.scope,
                OAuth2ApproveDO.deleted.is_(False),
            )
            .values(approved=update_obj.approved, expires_time=update_obj.expires_time)
        )
        result: Result = await self.write(stmt)
        return result.rowcount

    async def select_list_by_user_id_and_user_type_and_client_id(
        self, user_id: int, user_type: int, client_id: str
    ) -> list[OAuth2ApproveDO]:
        stmt = select(OAuth2ApproveDO).where(
            OAuth2ApproveDO.user_id == user_id,
            OAuth2ApproveDO.user_type == user_type,
            OAuth2ApproveDO.client_id == client_id,
        )
        result = await self.read(stmt)
        return list(result.scalars().all())
