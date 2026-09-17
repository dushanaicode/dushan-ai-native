from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OAuth2CodeService(Protocol):
    async def create_authorization_code(
        self, user_id, user_type, client_id, scopes, redirect_uri, state
    ) -> str: ...

    async def consume_authorization_code(self, code, *, client_id, redirect_uri, state): ...
