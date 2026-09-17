from typing import Protocol, runtime_checkable

from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.definitions.enums.notification.notification_channel_enum import (
    NotificationChannelEnum,
)
from module_system.framework.notification.model.notification_channel_result import (
    NotificationChannelResult,
)
from module_system.framework.notification.model.notification_dispatch_context import (
    NotificationDispatchContext,
)
from module_system.framework.notification.model.notification_recipient import NotificationRecipient


@runtime_checkable
class NotificationChannelHandler(Protocol):
    """
    通知渠道处理器接口
    定义了每个通知渠道（如站内信、短信、邮件）必须实现的契约。
    """

    @property
    def channel_type(self) -> NotificationChannelEnum:
        """返回当前处理器负责的渠道类型"""
        ...

    async def send(
        self,
        notice: NoticeDO,
        users: list[NotificationRecipient],
        notice_message_id_by_user_id: dict[int, int] | None = None,
        dispatch_context: NotificationDispatchContext | None = None,
    ) -> NotificationChannelResult:
        """发送通知"""
        ...
