from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.api.notification.dto.notice_send_dto import NoticeSendDTO
from module_system.controller.admin.notification.vo.notice.notice_page_req_vo import NoticePageReqVO
from module_system.controller.admin.notification.vo.notice.notice_save_req_vo import NoticeSaveReqVO
from module_system.controller.admin.notification.vo.notice.notice_send_req_vo import NoticeSendReqVO
from module_system.dal.dataobject.notification.notice_do import NoticeDO


@runtime_checkable
class NoticeService(Protocol):
    async def create_notice(self, create_req_vo: NoticeSaveReqVO) -> int: ...

    async def update_notice(self, update_req_vo: NoticeSaveReqVO) -> None: ...

    async def update_status(self, notice_id: int, status: int) -> None: ...

    async def delete_notice(self, id: int) -> None: ...

    async def delete_notice_batch(self, ids: list[int]) -> int: ...

    async def get_notice_page(self, req_vo: NoticePageReqVO) -> PageResult[NoticeDO]: ...

    async def get_notice(self, id: int) -> NoticeDO: ...

    async def send_notice(self, req: NoticeSendReqVO) -> None: ...

    async def send_notice_direct(self, req: NoticeSendDTO) -> int: ...
