from __future__ import annotations

from sqlalchemy import select

from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.dal.dataobject.oauth2.oauth2_code_do import OAuth2CodeDO


@mapper()
class OAuth2CodeMapper(BaseMapper[OAuth2CodeDO]):
    def __init__(self):
        super().__init__(OAuth2CodeDO)

    async def select_by_digest(self, code_digest: str) -> OAuth2CodeDO:
        stmt = select(OAuth2CodeDO).where(OAuth2CodeDO.code_digest == code_digest)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
