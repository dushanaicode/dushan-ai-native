from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.controller.admin.notification.vo.notice_message.notice_message_my_page_req_vo import (
    NoticeMessageMyPageReqVO,
)
from module_system.controller.admin.notification.vo.notice_message.notice_message_page_req_vo import (
    NoticeMessagePageReqVO,
)
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO
from module_system.service.notification.bo.notice_message_create_bo import NoticeMessageCreateBO


@runtime_checkable
class NoticeMessageService(Protocol):
    async def create_notice_message(self, req: NoticeMessageCreateBO) -> int: ...

    async def get_notice_message_page(
        self, req_vo: NoticeMessagePageReqVO
    ) -> PageResult[NoticeMessageDO]: ...

    async def get_my_notice_message_page(
        self, req_vo: NoticeMessageMyPageReqVO, user_id: int, user_type: int
    ) -> PageResult[NoticeMessageDO]: ...

    async def get_notice_message(self, id: int) -> NoticeMessageDO: ...

    async def get_unread_notice_message_list(
        self, user_id: int, user_type: int, size: int
    ) -> list[NoticeMessageDO]: ...

    async def get_unread_notice_message_count(self, user_id: int, user_type: int) -> int: ...

    async def update_notice_message_read(
        self, ids: Collection[int], user_id: int, user_type: int
    ) -> int: ...

    async def update_all_notice_message_read(self, user_id: int, user_type: int) -> int: ...
