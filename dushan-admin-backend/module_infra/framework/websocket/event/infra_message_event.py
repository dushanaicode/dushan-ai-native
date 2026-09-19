from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_web.public import (
    RoutePolicy,
)
from framework.starter_websocket.public import (
    EventDefinition,
    socket_event,
)
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
