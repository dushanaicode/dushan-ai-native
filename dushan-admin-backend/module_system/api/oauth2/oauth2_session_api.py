from typing import Protocol

from module_system.api.oauth2.dto.oauth2_session_dto import OAuth2SessionDTO


class OAuth2SessionApi(Protocol):
    async def list_sessions(self) -> list[OAuth2SessionDTO]: ...
    async def revoke_session(self, family_id: str) -> None: ...
