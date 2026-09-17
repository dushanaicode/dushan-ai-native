from typing import Annotated

from pydantic import Field

from module_system.controller.admin.notification.vo.notice_log.notice_log_message_vo import (
    NoticeLogMessageVO,
)
from module_system.controller.admin.notification.vo.notice_log.notice_log_resp_vo import (
    NoticeLogRespVO,
)


class NoticeLogDetailRespVO(NoticeLogRespVO):
    """管理后台 - 推送日志详情 Response VO"""

    messages: Annotated[
        list["NoticeLogMessageVO"] | None, Field(None, description="该批次的站内信消息列表")
    ]
