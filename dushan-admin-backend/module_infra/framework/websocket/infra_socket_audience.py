from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_websocket.decorators.socket_audience import socket_audience
from framework.starter_websocket.model.audience_definition import AudienceDefinition


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
