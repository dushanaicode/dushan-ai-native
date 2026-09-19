from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseDTO
from module_system.framework.notification.model.notice_publisher_info_dto import (
    NoticePublisherInfoDTO,
)


class NotificationDispatchContext(BaseDTO):
    """一次通知分发任务的显式上下文。"""

    notice_log_id: Annotated[int | None, Field(None, description="通知日志 ID")]
    publisher_info: Annotated[
        NoticePublisherInfoDTO | None, Field(None, description="发布者信息快照")
    ]
