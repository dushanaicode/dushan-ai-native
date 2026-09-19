from __future__ import annotations

from sqlalchemy import select

from framework.common.page import PageResult
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.notification.vo.notice_log.notice_log_page_req_vo import (
    NoticeLogPageReqVO,
)
from module_system.dal.dataobject.notification.notice_log_do import NoticeLogDO


@mapper()
class NoticeLogMapper(BaseMapper[NoticeLogDO]):
    def __init__(self):
        super().__init__(NoticeLogDO)

    async def select_page(self, req_vo: NoticeLogPageReqVO) -> PageResult[NoticeLogDO]:
        stmt = select(NoticeLogDO)
        if req_vo.notice_id is not None:
            stmt = stmt.where(NoticeLogDO.notice_id == req_vo.notice_id)
        if req_vo.notice_title is not None:
            stmt = stmt.where(NoticeLogDO.notice_title.like(f"%{req_vo.notice_title}%"))
        if req_vo.notice_type is not None:
            stmt = stmt.where(NoticeLogDO.notice_type == req_vo.notice_type)
        if req_vo.push_target_type is not None:
            stmt = stmt.where(NoticeLogDO.push_target_type == req_vo.push_target_type)
        if req_vo.push_status is not None:
            stmt = stmt.where(NoticeLogDO.push_status == req_vo.push_status)
        if req_vo.create_time and len(req_vo.create_time) == 2:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(NoticeLogDO.create_time.between(start_time, end_time))
        stmt = stmt.order_by(NoticeLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)
