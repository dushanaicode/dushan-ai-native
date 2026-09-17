from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.controller.admin.announcement.vo.announcement_page_req_vo import (
    AnnouncementPageReqVO,
)
from module_system.controller.admin.announcement.vo.announcement_save_req_vo import (
    AnnouncementSaveReqVO,
)
from module_system.dal.dataobject.announcement.announcement_do import AnnouncementDO


@runtime_checkable
class AnnouncementService(Protocol):
    async def create_announcement(self, req_vo: AnnouncementSaveReqVO) -> int: ...

    async def update_announcement(self, req_vo: AnnouncementSaveReqVO) -> bool: ...

    async def delete_announcement(self, id: int) -> bool: ...

    async def delete_announcement_batch(self, ids: list[int]) -> int: ...

    async def get_announcement(self, id: int) -> AnnouncementDO: ...

    async def get_announcement_page(
        self, page_req_vo: AnnouncementPageReqVO
    ) -> PageResult[AnnouncementDO]: ...

    async def expire_announcements(self, current_time: datetime) -> int: ...

    async def schedule_announcement_publish(self, id: int) -> bool: ...

    async def get_wait_publish_announcements(self) -> list[AnnouncementDO]: ...

    async def publish_announcement(self, id: int) -> bool: ...
