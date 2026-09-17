from typing import Protocol, runtime_checkable

from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.framework.notification.model.notification_dispatch_context import (
    NotificationDispatchContext,
)
from module_system.framework.notification.model.notification_recipient import NotificationRecipient


@runtime_checkable
class NotificationDispatcher(Protocol):
    """
    通知处理器编排器接口
    负责根据通知的渠道配置，调度一个或多个渠道处理器来完成发送任务。
    """

    async def send_notification(
        self,
        notice: NoticeDO,
        users: list[NotificationRecipient],
        dispatch_context: NotificationDispatchContext | None = None,
    ) -> set[int]:
        """创建站内信、提交渠道并记录结果，返回未成功提交的用户编号。"""
        ...
