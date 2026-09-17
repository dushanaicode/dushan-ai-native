from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.oauth2.dto.oauth2_access_token_resp_dto import OAuth2AccessTokenRespDTO


@runtime_checkable
class OAuth2GrantService(Protocol):
    async def grant_implicit(
        self, user_id: int, user_type: int, client_id: str, scopes: list
    ) -> OAuth2AccessTokenRespDTO: ...

    async def grant_authorization_code_for_code(
        self,
        user_id: int,
        user_type: int,
        client_id: str,
        scopes: list,
        redirect_uri: str,
        state: str,
    ) -> str: ...

    async def grant_authorization_code_for_access_token(
        self, client_id: str, code: str, redirect_uri: str, state: str
    ) -> OAuth2AccessTokenRespDTO: ...

    async def grant_password(
        self, username: str, password: str, client_id: str, scopes: list, user_type: int
    ) -> OAuth2AccessTokenRespDTO: ...

    async def grant_refresh_token(
        self, refresh_token: str, client_id: str
    ) -> OAuth2AccessTokenRespDTO: ...

    async def grant_client_credentials(
        self, client_id: str, scopes: list
    ) -> OAuth2AccessTokenRespDTO: ...

    async def revoke_token(self, client_id: str, access_token: str) -> bool: ...
