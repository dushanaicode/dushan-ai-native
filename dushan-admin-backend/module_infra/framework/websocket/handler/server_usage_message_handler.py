from framework.starter_di.decorators.inject import Inject
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_websocket.decorators.socket_handler import socket_handler
from framework.starter_websocket.model.handler_definition import HandlerDefinition
from module_infra.framework.websocket.handler.system_message_handler_base import (
    SystemMessageHandlerBase,
)
from module_infra.framework.websocket.infra_socket_request import InfraSocketRequest
from module_infra.service.server.server_service import ServerService


@socket_handler(
    HandlerDefinition(
        audience="infra",
        type="get-server-usage-data",
        payload=InfraSocketRequest,
        policy=RoutePolicy(
            permissions=("infra:server:query",), tenant_required=True, realm=SecurityRealm.TENANT
        ),
    )
)
class ServerUsageMessageHandler(SystemMessageHandlerBase):
    service: ServerService = Inject()
    security: SecurityContext = Inject()
    response_type = "get-server-usage-data-response"

    async def process_message(self):
        return (await self.service.get_server_usage()).model_dump(mode="json", by_alias=True)
