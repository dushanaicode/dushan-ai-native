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
        key="system",
        policy=RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        send_policy=RoutePolicy(
            permissions=("system:notification:send", "system:announcement:update"),
            permission_mode="any",
            tenant_required=True,
            realm=SecurityRealm.TENANT,
        ),
        workload_capability="system.announcement.publish",
        allow_global_targets=False,
    )
)
class NoticeSocketAudience:
    """系统通知的连接域与发送授权声明。"""
