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
from module_system.framework.notification.websocket.notice_realtime_payload import (
    NoticeRealtimePayload,
)
from module_system.framework.notification.websocket.notice_realtime_projection import (
    NoticeRealtimeProjection,
)


@socket_event(
    EventDefinition(
        audience="system",
        type="notification",
        payload=NoticeRealtimePayload,
        policy=RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        projector=NoticeRealtimeProjection,
    )
)
class NoticeSocketEvent:
    """仅推送记录定位，接收端在自己的权限范围内重新读取。"""
