from __future__ import annotations

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.mail.vo.log.log_page_req_vo import MailLogPageReqVO
from module_system.dal.dataobject.mail.mail_log_do import MailLogDO


@mapper()
class MailLogMapper(BaseMapper[MailLogDO]):
    def __init__(self):
        super().__init__(MailLogDO)

    async def select_page(self, req_vo: MailLogPageReqVO) -> PageResult[MailLogDO]:
        stmt = select(MailLogDO)
        if req_vo.user_id is not None:
            stmt = stmt.where(MailLogDO.user_id == req_vo.user_id)
        if req_vo.user_type is not None:
            stmt = stmt.where(MailLogDO.user_type == req_vo.user_type)
        if req_vo.to_mail:
            escaped = StrUtils.escape_like(req_vo.to_mail)
            stmt = stmt.where(MailLogDO.to_mail.ilike(f"%{escaped}%"))
        if req_vo.account_id is not None:
            stmt = stmt.where(MailLogDO.account_id == req_vo.account_id)
        if req_vo.template_id is not None:
            stmt = stmt.where(MailLogDO.template_id == req_vo.template_id)
        if req_vo.send_status is not None:
            stmt = stmt.where(MailLogDO.send_status == req_vo.send_status)
        if req_vo.send_time_begin and req_vo.send_time_end:
            stmt = stmt.where(
                MailLogDO.send_time.between(req_vo.send_time_begin, req_vo.send_time_end)
            )
        stmt = stmt.order_by(MailLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)
