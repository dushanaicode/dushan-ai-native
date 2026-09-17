from typing import Protocol, runtime_checkable

from module_system.api.oauth2.dto.oauth2_session_dto import OAuth2SessionDTO


@runtime_checkable
class OAuth2SessionService(Protocol):
    async def list_sessions(self) -> list[OAuth2SessionDTO]: ...
    async def revoke_session(self, family_id: str) -> None: ...
