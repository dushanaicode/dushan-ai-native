from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select, update

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
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
        async with self._get_session_scope(for_write=True) as session:
            result = await session.execute(
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
            escaped = StrUtils.escape_like(req_vo.title)
            stmt = stmt.where(AnnouncementDO.title.ilike(f"%{escaped}%"))
        if req_vo.status is not None:
            stmt = stmt.where(AnnouncementDO.status == req_vo.status)
        if req_vo.is_top is not None:
            stmt = stmt.where(AnnouncementDO.is_top == req_vo.is_top)
        if req_vo.category is not None:
            stmt = stmt.where(AnnouncementDO.category == req_vo.category)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                AnnouncementDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
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
