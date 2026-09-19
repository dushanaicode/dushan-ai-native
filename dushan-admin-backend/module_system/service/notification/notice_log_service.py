from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.controller.admin.notification.vo.notice_log.notice_log_page_req_vo import (
    NoticeLogPageReqVO,
)
from module_system.dal.dataobject.notification.notice_log_do import NoticeLogDO
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO
from module_system.service.notification.bo.notice_log_create_bo import NoticeLogCreateBO
from module_system.service.notification.bo.notice_log_result_bo import NoticeLogResultBO


@runtime_checkable
class NoticeLogService(Protocol):
    async def create_notice_log(self, req: NoticeLogCreateBO) -> int: ...

    async def update_notice_log_result(self, req: NoticeLogResultBO) -> None: ...

    async def get_notice_log_page(self, req_vo: NoticeLogPageReqVO) -> PageResult[NoticeLogDO]: ...

    async def get_notice_log(self, notice_log_id: int) -> NoticeLogDO | None: ...

    async def get_notice_log_messages(self, notice_log_id: int) -> list[NoticeMessageDO]: ...
