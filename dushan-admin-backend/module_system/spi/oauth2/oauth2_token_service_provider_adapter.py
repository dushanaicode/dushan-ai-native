from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.spi.token_provider import TokenProvider
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
