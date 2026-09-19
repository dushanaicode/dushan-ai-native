from functools import partial
from uuid import uuid4

from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_tenant.public import (
    TenantContext,
)
from framework.starter_websocket.public import (
    SocketMessage,
    SocketTarget,
    SocketTargetKind,
    WebSocketService,
    WebSocketSettings,
)
from module_system.definitions.enums.notification.notification_channel_enum import (
    NotificationChannelEnum,
)
from module_system.framework.notification.channel.notification_channel_handler import (
    NotificationChannelHandler,
)
from module_system.framework.notification.model.notification_channel_result import (
    NotificationChannelResult,
)


@service(providers=[NotificationChannelHandler])
class InternalNotificationHandler(NotificationChannelHandler):
    websocket: WebSocketService = Inject()
    tenant: TenantContext = Inject()
    settings: WebSocketSettings = Inject()
    database: SessionProvider = Inject()

    @property
    def channel_type(self):
        return NotificationChannelEnum.INTERNAL

    @transactional
    async def send(self, notice, users, notice_message_id_by_user_id=None, dispatch_context=None):
        if self.settings.enabled:
            self.database.after_commit(
                partial(
                    self._send_realtime,
                    self.tenant.get_required_tenant_id(),
                    {user.id: notice_message_id_by_user_id[user.id] for user in users},
                ),
                name="notification-realtime",
            )
        return NotificationChannelResult(
            channel_code=self.channel_type.code, success_user_ids={user.id for user in users}
        )

    async def _send_realtime(self, tenant_id: str, messages: dict[int, int]) -> None:
        """站内信提交后再发送提示，接收者可以立即读取已提交的消息。"""
        for user_id, message_id in messages.items():
            await self.websocket.send(
                SocketTarget(
                    kind=SocketTargetKind.MEMBER,
                    audience="system",
                    tenant_id=tenant_id,
                    member_id=str(user_id),
                ),
                SocketMessage(
                    type="notification",
                    payload={"messageId": str(message_id)},
                    request_id=uuid4().hex,
                ),
            )
