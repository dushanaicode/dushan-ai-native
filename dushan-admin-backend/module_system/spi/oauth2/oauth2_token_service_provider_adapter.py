from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    LoginSession,
    TokenProvider,
)
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService


@service(interface=TokenProvider)
class OAuth2TokenServiceProviderAdapter(TokenProvider):
    delegate: OAuth2TokenService = Inject()

    @override
    async def resolve(
        self, token_digest: str, *, application_id: str, domain: str
    ) -> LoginSession | None:
        return await self.delegate.resolve_session(
            token_digest, application_id=application_id, domain=domain
        )

    @override
    async def revoke(self, session: LoginSession) -> None:
        return await self.delegate.revoke_session(session)
