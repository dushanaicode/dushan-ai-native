from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    TokenProvider,
)
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService


@service(interface=TokenProvider)
class OAuth2TokenServiceProviderAdapter(TokenProvider):
    delegate: OAuth2TokenService = Inject()

    async def resolve(self, token_digest: str, *, application_id: str, domain: str):
        return await self.delegate.resolve_session(
            token_digest, application_id=application_id, domain=domain
        )

    async def revoke(self, session):
        return await self.delegate.revoke_session(session)
