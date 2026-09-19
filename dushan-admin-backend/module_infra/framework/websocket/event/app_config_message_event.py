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
from module_infra.framework.websocket.infra_socket_payload import InfraSocketPayload


@socket_event(
    EventDefinition(
        audience="infra",
        type="get-app-config-response",
        payload=InfraSocketPayload,
        policy=RoutePolicy(
            permissions=("infra:config:query",), tenant_required=True, realm=SecurityRealm.TENANT
        ),
        projector=None,
    )
)
class AppConfigMessageEvent:
    pass
