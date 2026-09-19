from framework.starter_di.public import (
    Inject,
)
from framework.starter_security.public import (
    SecurityContext,
    SecurityRealm,
)
from framework.starter_web.public import (
    RoutePolicy,
)
from framework.starter_websocket.public import (
    HandlerDefinition,
    socket_handler,
)
from module_infra.api.config.config_api import ConfigApi
from module_infra.framework.websocket.handler.system_message_handler_base import (
    SystemMessageHandlerBase,
)
from module_infra.framework.websocket.infra_socket_request import InfraSocketRequest


@socket_handler(
    HandlerDefinition(
        audience="infra",
        type="get-app-config",
        payload=InfraSocketRequest,
        policy=RoutePolicy(
            permissions=("infra:config:query",), tenant_required=True, realm=SecurityRealm.TENANT
        ),
    )
)
class AppConfigMessageHandler(SystemMessageHandlerBase):
    service: ConfigApi = Inject()
    security: SecurityContext = Inject()
    response_type = "get-app-config-response"

    async def process_message(self):
        return await self.service.get_all_by_module("system")
