from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.notification.dto.notice_send_dto import NoticeSendDTO
from module_system.api.notification.notice_api import NoticeApi
from module_system.service.notification.notice_service import NoticeService


@service(interface=NoticeApi)
class NoticeApiImpl(NoticeApi):
    """通知 API 实现"""

    notice_service: NoticeService = Inject()

    @override
    async def send_notice_direct(self, dto: NoticeSendDTO) -> int:
        return await self.notice_service.send_notice_direct(dto)
