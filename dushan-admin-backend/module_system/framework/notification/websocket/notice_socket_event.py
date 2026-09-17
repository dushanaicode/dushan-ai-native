from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_websocket.decorators.socket_event import socket_event
from framework.starter_websocket.model.event_definition import EventDefinition
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
