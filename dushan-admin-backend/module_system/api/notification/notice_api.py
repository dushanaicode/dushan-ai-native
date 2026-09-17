from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.notification.dto.notice_send_dto import NoticeSendDTO


@runtime_checkable
class NoticeApi(Protocol):
    """通知 API 接口"""

    async def send_notice_direct(self, dto: NoticeSendDTO) -> int:
        """使用指定内置模板发送动态通知。"""
        ...
