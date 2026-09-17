from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_websocket.decorators.socket_event import socket_event
from framework.starter_websocket.model.event_definition import EventDefinition
from module_infra.controller.admin.websocket.vo.websocket_message_vo import WebsocketMessageVO


@socket_event(
    EventDefinition(
        audience="infra",
        type="infra-message",
        payload=WebsocketMessageVO,
        policy=RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        projector=None,
    )
)
class InfraMessageEvent:
    pass
