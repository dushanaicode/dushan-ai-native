from framework.starter_auth.config.auth_client_config import AuthClientConfig
from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_auth.spi.auth_client_provider import AuthClientProvider
from framework.starter_di.decorators.components import framework


@framework(interface=AuthClientProvider)
class ConfiguredAuthClients(AuthClientProvider):
    def __init__(self, settings: AuthSettings) -> None:
        self._clients = {
            (c.application_id, c.source): c.model_copy(deep=True) for c in settings.clients
        }

    async def get_client(self, application_id: str, source: str) -> AuthClientConfig | None:
        config = self._clients.get((application_id, source))
        return None if config is None else config.model_copy(deep=True)
