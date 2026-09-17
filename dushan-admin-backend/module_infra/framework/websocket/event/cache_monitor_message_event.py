from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_websocket.decorators.socket_event import socket_event
from framework.starter_websocket.model.event_definition import EventDefinition
from module_infra.framework.websocket.infra_socket_payload import InfraSocketPayload


@socket_event(
    EventDefinition(
        audience="infra",
        type="get-cache-monitor-data-response",
        payload=InfraSocketPayload,
        policy=RoutePolicy(
            permissions=("infra:cache:query",), tenant_required=True, realm=SecurityRealm.TENANT
        ),
        projector=None,
    )
)
class CacheMonitorMessageEvent:
    pass
