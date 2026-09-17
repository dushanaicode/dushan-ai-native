from __future__ import annotations

from collections.abc import Collection
from datetime import datetime

from sqlalchemy import MergedResult, func, select, update

from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.notification.vo.notice_message.notice_message_my_page_req_vo import (
    NoticeMessageMyPageReqVO,
)
from module_system.controller.admin.notification.vo.notice_message.notice_message_page_req_vo import (
    NoticeMessagePageReqVO,
)
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO


@mapper()
class NoticeMessageMapper(BaseMapper[NoticeMessageDO]):
    def __init__(self):
        super().__init__(NoticeMessageDO)

    async def select_page(self, req_vo: NoticeMessagePageReqVO) -> PageResult[NoticeMessageDO]:
        stmt = select(NoticeMessageDO)
        if req_vo.user_id is not None:
            stmt = stmt.where(NoticeMessageDO.user_id == req_vo.user_id)
        if req_vo.user_type is not None:
            stmt = stmt.where(NoticeMessageDO.user_type == req_vo.user_type)
        if req_vo.notice_id is not None:
            stmt = stmt.where(NoticeMessageDO.notice_id == req_vo.notice_id)
        if req_vo.read_status is not None:
            stmt = stmt.where(NoticeMessageDO.read_status == req_vo.read_status)
        if req_vo.notice_title is not None:
            stmt = stmt.where(NoticeMessageDO.notice_title.like(f"%{req_vo.notice_title}%"))
        if req_vo.notice_type is not None:
            stmt = stmt.where(NoticeMessageDO.notice_type == req_vo.notice_type)
        if req_vo.create_time and len(req_vo.create_time) == 2:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(NoticeMessageDO.create_time.between(start_time, end_time))
        stmt = stmt.order_by(NoticeMessageDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_page_my(
        self, req_vo: NoticeMessageMyPageReqVO, user_id: int, user_type: int
    ) -> PageResult[NoticeMessageDO]:
        stmt = select(NoticeMessageDO)
        if req_vo.read_status is not None:
            stmt = stmt.where(NoticeMessageDO.read_status == req_vo.read_status)
        if (
            req_vo.create_time
            and isinstance(req_vo.create_time, (list, tuple))
            and (len(req_vo.create_time) == 2)
        ):
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(NoticeMessageDO.create_time.between(start_time, end_time))
        if req_vo.notice_title is not None:
            stmt = stmt.where(NoticeMessageDO.notice_title.like(f"%{req_vo.notice_title}%"))
        if req_vo.notice_type is not None:
            stmt = stmt.where(NoticeMessageDO.notice_type == req_vo.notice_type)
        stmt = stmt.where(
            NoticeMessageDO.user_id == user_id, NoticeMessageDO.user_type == user_type
        )
        stmt = stmt.order_by(NoticeMessageDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def update_list_read(self, ids: Collection[int], user_id: int, user_type: int) -> int:
        stmt = (
            update(NoticeMessageDO)
            .where(
                NoticeMessageDO.id.in_(ids),
                NoticeMessageDO.user_id == user_id,
                NoticeMessageDO.user_type == user_type,
                NoticeMessageDO.read_status.is_(False),
                NoticeMessageDO.deleted.is_(False),
            )
            .values(read_status=True, read_time=datetime.now())
        )
        result: MergedResult = await self.write(stmt)
        return result.rowcount

    async def update_list_read_all(self, user_id: int, user_type: int) -> int:
        stmt = (
            update(NoticeMessageDO)
            .where(
                NoticeMessageDO.user_id == user_id,
                NoticeMessageDO.user_type == user_type,
                NoticeMessageDO.read_status.is_(False),
                NoticeMessageDO.deleted.is_(False),
            )
            .values(read_status=True, read_time=datetime.now())
        )
        result: MergedResult = await self.write(stmt)
        return result.rowcount

    async def select_unread_list_by_user_id_and_user_type(
        self, user_id: int, user_type: int, size: int
    ) -> list[NoticeMessageDO]:
        stmt = (
            select(NoticeMessageDO)
            .where(
                NoticeMessageDO.user_id == user_id,
                NoticeMessageDO.user_type == user_type,
                NoticeMessageDO.read_status.is_(False),
            )
            .order_by(NoticeMessageDO.id.desc())
            .limit(size)
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_unread_count_by_user_id_and_user_type(
        self, user_id: int, user_type: int
    ) -> int:
        stmt = select(func.count(NoticeMessageDO.id)).where(
            NoticeMessageDO.user_id == user_id,
            NoticeMessageDO.user_type == user_type,
            NoticeMessageDO.read_status.is_(False),
        )
        result = await self.read(stmt)
        count = result.scalar_one_or_none()
        return count if count is not None else 0
