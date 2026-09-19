from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.starter_security.public import (
    LoginSession,
)
from module_system.api.oauth2.dto.oauth2_access_token_resp_dto import OAuth2AccessTokenRespDTO
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO


@runtime_checkable
class OAuth2TokenService(Protocol):
    async def create_access_token(
        self, user_id: int, user_type: int, client_id: str, scopes: list[str]
    ) -> OAuth2AccessTokenRespDTO: ...

    async def refresh_access_token(
        self, refresh_token: str, client_id: str
    ) -> OAuth2AccessTokenRespDTO: ...

    async def resolve_session(
        self, token_digest: str, *, application_id: str, domain: str
    ) -> LoginSession | None: ...

    async def check_access_token(self, access_token: str) -> OAuth2AccessTokenDO: ...

    async def get_access_token(self, access_token: str) -> OAuth2AccessTokenDO | None: ...

    async def revoke_session(self, session: LoginSession): ...

    async def remove_access_token(self, access_token: str): ...

    async def remove_access_token_batch(self, ids: list[int]) -> int: ...

    async def get_access_token_page(self, req_vo): ...

    async def get_access_tokens_by_user_id(self, user_id: int, user_type: int): ...

    async def verify_token_and_get_user(
        self, token: str, user_type: int | None = None
    ) -> LoginSession: ...

    async def build_user_info(self, user_id: int, user_type: int) -> dict: ...

    async def create_socket_ticket(self, identity: LoginSession) -> str: ...

    async def consume_socket_ticket(
        self, ticket: str, *, application_id: str, domain: str
    ) -> LoginSession: ...
