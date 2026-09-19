from __future__ import annotations

from sqlalchemy import select

from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.dal.dataobject.oauth2.oauth2_refresh_token_do import OAuth2RefreshTokenDO


@mapper
class OAuth2RefreshTokenMapper(BaseMapper[OAuth2RefreshTokenDO]):
    def __init__(self):
        super().__init__(OAuth2RefreshTokenDO)

    async def select_by_digest(self, token_digest: str) -> OAuth2RefreshTokenDO | None:
        result = await self.read_from_primary(
            select(OAuth2RefreshTokenDO).where(OAuth2RefreshTokenDO.token_digest == token_digest)
        )
        return result.scalar_one_or_none()

    async def revoke_family(self, family_id: str) -> int:
        return await self.update_by_condition(
            {"revoked": True}, OAuth2RefreshTokenDO.family_id == family_id
        )
