from __future__ import annotations

from sqlalchemy import select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.sms.vo.channel.sms_channel_page_req_vo import (
    SmsChannelPageReqVO,
)
from module_system.dal.dataobject.sms.sms_channel_do import SmsChannelDO


@mapper()
class SmsChannelMapper(BaseMapper[SmsChannelDO]):
    def __init__(self):
        super().__init__(SmsChannelDO)

    async def select_page(self, req_vo: SmsChannelPageReqVO) -> PageResult[SmsChannelDO]:
        stmt = select(SmsChannelDO)
        if req_vo.signature:
            escaped_sig = StrUtils.escape_like(req_vo.signature)
            stmt = stmt.where(SmsChannelDO.signature.ilike(f"%{escaped_sig}%", escape="\\"))
        if req_vo.status is not None:
            stmt = stmt.where(SmsChannelDO.status == req_vo.status)
        if req_vo.code:
            escaped_code = StrUtils.escape_like(req_vo.code)
            stmt = stmt.where(SmsChannelDO.code.ilike(f"%{escaped_code}%", escape="\\"))
        if req_vo.create_time is not None:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(SmsChannelDO.create_time.between(start_time, end_time))
        stmt = stmt.order_by(SmsChannelDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_code(self, code: str) -> SmsChannelDO | None:
        stmt = select(SmsChannelDO).where(SmsChannelDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
