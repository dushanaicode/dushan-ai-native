from __future__ import annotations

from sqlalchemy import func, or_, select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
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
            escaped = StrUtils.escape_like(req_vo.title)
            stmt = stmt.where(NoticeDO.title.ilike(f"%{escaped}%"))
        if req_vo.type is not None:
            stmt = stmt.where(NoticeDO.type == req_vo.type)
        if req_vo.status is not None:
            stmt = stmt.where(NoticeDO.status == req_vo.status)
        if req_vo.publisher is not None:
            escaped_pub = StrUtils.escape_like(req_vo.publisher)
            stmt = stmt.where(NoticeDO.publisher.ilike(f"%{escaped_pub}%"))
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                NoticeDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        if req_vo.user_type is not None:
            stmt = stmt.where(NoticeDO.user_type == req_vo.user_type)
        if req_vo.channels:
            json_conditions = [
                func.JSON_CONTAINS(NoticeDO.channels, f'"{ch}"') for ch in req_vo.channels
            ]
            if json_conditions:
                stmt = stmt.where(or_(*json_conditions))
        stmt = stmt.order_by(NoticeDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def update(self, notice: NoticeDO) -> None:
        await self.update_by_id(notice)

    async def select_by_code(self, code: str) -> NoticeDO | None:
        """按通知编码查询内置模板"""
        stmt = select(NoticeDO).where(NoticeDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
