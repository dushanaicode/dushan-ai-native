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
        type="get-server-monitor-data-response",
        payload=InfraSocketPayload,
        policy=RoutePolicy(
            permissions=("infra:server:query",), tenant_required=True, realm=SecurityRealm.TENANT
        ),
        projector=None,
    )
)
class ServerMonitorMessageEvent:
    pass
