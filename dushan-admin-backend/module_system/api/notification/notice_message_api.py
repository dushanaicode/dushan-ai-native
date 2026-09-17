from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.notification.dto.notice_message_mark_read_req_dto import (
    NoticeMessageMarkReadReqDTO,
)


@runtime_checkable
class NoticeMessageApi(Protocol):
    """站内信跨模块 API。"""

    async def mark_read(self, req: NoticeMessageMarkReadReqDTO) -> int:
        """在指定用户范围内标记站内信为已读。"""
        ...
