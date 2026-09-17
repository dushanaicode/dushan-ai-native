from __future__ import annotations

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.sms.vo.log.log_page_req_vo import SmsLogPageReqVO
from module_system.dal.dataobject.sms.sms_log_do import SmsLogDO


@mapper()
class SmsLogMapper(BaseMapper[SmsLogDO]):
    def __init__(self):
        super().__init__(SmsLogDO)

    async def select_page(self, req_vo: SmsLogPageReqVO) -> PageResult[SmsLogDO]:
        stmt = select(SmsLogDO)
        if req_vo.channel_id is not None:
            stmt = stmt.where(SmsLogDO.channel_id == req_vo.channel_id)
        if req_vo.template_id is not None:
            stmt = stmt.where(SmsLogDO.template_id == req_vo.template_id)
        if req_vo.mobile:
            escaped = StrUtils.escape_like(req_vo.mobile)
            stmt = stmt.where(SmsLogDO.mobile.ilike(f"%{escaped}%"))
        if req_vo.send_status is not None:
            stmt = stmt.where(SmsLogDO.send_status == req_vo.send_status)
        if req_vo.send_time and len(req_vo.send_time) == 2:
            stmt = stmt.where(SmsLogDO.send_time.between(req_vo.send_time[0], req_vo.send_time[1]))
        if req_vo.receive_status is not None:
            stmt = stmt.where(SmsLogDO.receive_status == req_vo.receive_status)
        if req_vo.receive_time and len(req_vo.receive_time) == 2:
            stmt = stmt.where(
                SmsLogDO.receive_time.between(req_vo.receive_time[0], req_vo.receive_time[1])
            )
        stmt = stmt.order_by(SmsLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)
