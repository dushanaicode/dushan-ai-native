from __future__ import annotations

from sqlalchemy import or_, select

from framework.common.page import PageResult
from framework.starter_database.model.json_array_contains import JsonArrayContains
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.notification.vo.notice.notice_page_req_vo import NoticePageReqVO
from module_system.dal.dataobject.notification.notice_do import NoticeDO


@mapper()
class NoticeMapper(BaseMapper[NoticeDO]):
    def __init__(self):
        super().__init__(NoticeDO)

    async def select_page(self, req_vo: NoticePageReqVO) -> PageResult[NoticeDO]:
        stmt = select(NoticeDO)
        if req_vo.title:
            stmt = stmt.where(NoticeDO.title.icontains(req_vo.title, autoescape=True, escape="\\"))
        if req_vo.type is not None:
            stmt = stmt.where(NoticeDO.type == req_vo.type)
        if req_vo.status is not None:
            stmt = stmt.where(NoticeDO.status == req_vo.status)
        if req_vo.publisher is not None:
            stmt = stmt.where(
                NoticeDO.publisher.icontains(req_vo.publisher, autoescape=True, escape="\\")
            )
        if req_vo.create_time is not None:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(NoticeDO.create_time.between(start_time, end_time))
        if req_vo.user_type is not None:
            stmt = stmt.where(NoticeDO.user_type == req_vo.user_type)
        if req_vo.channels:
            stmt = stmt.where(
                or_(*(JsonArrayContains(NoticeDO.channels, ch) for ch in req_vo.channels))
            )
        stmt = stmt.order_by(NoticeDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def update(self, notice: NoticeDO) -> None:
        await self.update_by_id(notice)

    async def select_by_code(self, code: str) -> NoticeDO | None:
        """按通知编码查询内置模板"""
        stmt = select(NoticeDO).where(NoticeDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
