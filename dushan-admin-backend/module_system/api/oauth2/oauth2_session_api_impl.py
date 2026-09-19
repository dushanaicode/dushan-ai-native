from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.oauth2.dto.oauth2_session_dto import OAuth2SessionDTO
from module_system.api.oauth2.oauth2_session_api import OAuth2SessionApi
from module_system.service.oauth2.oauth2_session_service import OAuth2SessionService


@service(interface=OAuth2SessionApi)
class OAuth2SessionApiImpl(OAuth2SessionApi):
    sessions: OAuth2SessionService = Inject()

    async def list_sessions(self) -> list[OAuth2SessionDTO]:
        return await self.sessions.list_sessions()

    async def revoke_session(self, family_id: str) -> None:
        await self.sessions.revoke_session(family_id)
