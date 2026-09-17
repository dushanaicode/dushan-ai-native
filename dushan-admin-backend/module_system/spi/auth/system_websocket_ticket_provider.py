from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_websocket.spi.websocket_ticket_provider import WebSocketTicketProvider
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService


@service(interface=WebSocketTicketProvider)
class SystemWebSocketTicketProvider(WebSocketTicketProvider):
    tokens: OAuth2TokenService = Inject()

    async def consume(self, ticket: str, *, application_id: str, domain: str):
        return await self.tokens.consume_socket_ticket(
            ticket, application_id=application_id, domain=domain
        )
