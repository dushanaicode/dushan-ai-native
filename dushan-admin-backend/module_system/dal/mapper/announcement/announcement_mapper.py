from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select, update

from framework.common.page import PageResult
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.announcement.vo.announcement_page_req_vo import (
    AnnouncementPageReqVO,
)
from module_system.dal.dataobject.announcement.announcement_do import AnnouncementDO
from module_system.definitions.enums.announcement.announcement_status_enum import (
    AnnouncementStatusEnum,
)


@mapper()
class AnnouncementMapper(BaseMapper[AnnouncementDO]):
    def __init__(self):
        super().__init__(AnnouncementDO)

    async def select_for_update(self, identifier: int) -> AnnouncementDO | None:
        """在当前写事务中锁定公告，供发布操作检查并更新。"""
        result = await self.execute(
            select(AnnouncementDO).where(AnnouncementDO.id == identifier).with_for_update()
        )
        return result.scalar_one_or_none()

    async def expire_published(self, current_time: datetime) -> int:
        result = await self.write(
            update(AnnouncementDO)
            .where(
                AnnouncementDO.status == AnnouncementStatusEnum.PUBLISHED.code,
                AnnouncementDO.expire_time <= current_time,
            )
            .values(status=AnnouncementStatusEnum.EXPIRED.code)
        )
        return result.rowcount

    async def select_page(self, req_vo: AnnouncementPageReqVO) -> PageResult[AnnouncementDO]:
        stmt = select(AnnouncementDO)
        if req_vo.title:
            stmt = stmt.where(
                AnnouncementDO.title.icontains(req_vo.title, autoescape=True, escape="\\")
            )
        if req_vo.status is not None:
            stmt = stmt.where(AnnouncementDO.status == req_vo.status)
        if req_vo.is_top is not None:
            stmt = stmt.where(AnnouncementDO.is_top == req_vo.is_top)
        if req_vo.category is not None:
            stmt = stmt.where(AnnouncementDO.category == req_vo.category)
        if req_vo.create_time is not None:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(AnnouncementDO.create_time.between(start_time, end_time))
        stmt = stmt.order_by(
            AnnouncementDO.is_top.desc(), AnnouncementDO.sort.asc(), AnnouncementDO.id.desc()
        )
        return await self.paginate_query(stmt, req_vo)

    async def select_list_by_status(self, status: int) -> list[AnnouncementDO]:
        stmt = select(AnnouncementDO).where(AnnouncementDO.status == status)
        stmt = stmt.order_by(
            AnnouncementDO.is_top.desc(), AnnouncementDO.sort.asc(), AnnouncementDO.id.desc()
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_status_and_publish_time_le(
        self, status: int, publish_time: datetime
    ) -> list[AnnouncementDO]:
        stmt = select(AnnouncementDO).where(
            AnnouncementDO.status == status, AnnouncementDO.publish_time <= publish_time
        )
        stmt = stmt.order_by(
            AnnouncementDO.is_top.desc(), AnnouncementDO.sort.asc(), AnnouncementDO.id.desc()
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_pending_announcements(self, current_time: datetime) -> list[AnnouncementDO]:
        stmt = select(AnnouncementDO).where(
            AnnouncementDO.status == AnnouncementStatusEnum.WAIT_PUBLISH.code,
            AnnouncementDO.publish_time <= current_time,
        )
        stmt = stmt.order_by(
            AnnouncementDO.is_top.desc(), AnnouncementDO.sort.asc(), AnnouncementDO.id.desc()
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_status_and_expire_time_le(
        self, status: int, expire_time: datetime
    ) -> list[AnnouncementDO]:
        stmt = select(AnnouncementDO).where(
            AnnouncementDO.status == status,
            AnnouncementDO.expire_time.isnot(None),
            AnnouncementDO.expire_time <= expire_time,
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_published_announcements(self, current_time: datetime) -> list[AnnouncementDO]:
        stmt = select(AnnouncementDO).where(
            AnnouncementDO.status == AnnouncementStatusEnum.PUBLISHED.code,
            or_(AnnouncementDO.expire_time.is_(None), AnnouncementDO.expire_time > current_time),
        )
        stmt = stmt.order_by(
            AnnouncementDO.is_top.desc(), AnnouncementDO.sort.asc(), AnnouncementDO.id.desc()
        )
        result = await self.read(stmt)
        return list(result.scalars().all())
