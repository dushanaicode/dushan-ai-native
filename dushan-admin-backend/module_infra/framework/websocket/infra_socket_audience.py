from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_web.public import (
    RoutePolicy,
)
from framework.starter_websocket.public import (
    AudienceDefinition,
    socket_audience,
)


@socket_audience(
    AudienceDefinition(
        key="infra",
        policy=RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        send_policy=RoutePolicy(
            permissions=("infra:websocket:send",), tenant_required=True, realm=SecurityRealm.TENANT
        ),
        workload_capability=None,
        allow_global_targets=False,
    )
)
class InfraSocketAudience:
    pass
