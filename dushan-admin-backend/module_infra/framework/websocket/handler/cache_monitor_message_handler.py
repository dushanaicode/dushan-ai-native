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
from module_infra.service.cache.cache_service import CacheService


@socket_handler(
    HandlerDefinition(
        audience="infra",
        type="get-cache-monitor-data",
        payload=InfraSocketRequest,
        policy=RoutePolicy(
            permissions=("infra:cache:query",), tenant_required=True, realm=SecurityRealm.TENANT
        ),
    )
)
class CacheMonitorMessageHandler(SystemMessageHandlerBase):
    service: CacheService = Inject()
    security: SecurityContext = Inject()
    response_type = "get-cache-monitor-data-response"

    async def process_message(self):
        return (await self.service.get_cache_monitor_info()).model_dump(mode="json", by_alias=True)
