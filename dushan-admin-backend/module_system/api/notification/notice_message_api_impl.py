from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.notification.dto.notice_message_mark_read_req_dto import (
    NoticeMessageMarkReadReqDTO,
)
from module_system.api.notification.notice_message_api import NoticeMessageApi
from module_system.service.notification.notice_message_service import (
    NoticeMessageService,
)


@service(interface=NoticeMessageApi)
class NoticeMessageApiImpl(NoticeMessageApi):
    """站内信跨模块 API 实现。"""

    notice_message_service: NoticeMessageService = Inject()

    @override
    async def mark_read(self, req: NoticeMessageMarkReadReqDTO) -> int:
        return await self.notice_message_service.update_notice_message_read(
            ids=[req.notice_message_id], user_id=req.user_id, user_type=req.user_type
        )
