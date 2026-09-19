from __future__ import annotations

from sqlalchemy import func, select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.sms.vo.template.template_page_req_vo import SmsTemplatePageReqVO
from module_system.dal.dataobject.sms.sms_template_do import SmsTemplateDO


@mapper()
class SmsTemplateMapper(BaseMapper[SmsTemplateDO]):
    def __init__(self):
        super().__init__(SmsTemplateDO)

    async def select_by_code(self, code: str) -> SmsTemplateDO | None:
        stmt = select(SmsTemplateDO).where(SmsTemplateDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_page(self, req_vo: SmsTemplatePageReqVO) -> PageResult[SmsTemplateDO]:
        stmt = select(SmsTemplateDO)
        if req_vo.type is not None:
            stmt = stmt.where(SmsTemplateDO.type == req_vo.type)
        if req_vo.status is not None:
            stmt = stmt.where(SmsTemplateDO.status == req_vo.status)
        if req_vo.code:
            escaped_code = StrUtils.escape_like(req_vo.code)
            stmt = stmt.where(SmsTemplateDO.code.ilike(f"%{escaped_code}%"))
        if req_vo.content:
            escaped_content = StrUtils.escape_like(req_vo.content)
            stmt = stmt.where(SmsTemplateDO.content.ilike(f"%{escaped_content}%"))
        if req_vo.channel_id is not None:
            stmt = stmt.where(SmsTemplateDO.channel_id == req_vo.channel_id)
        if req_vo.create_time and len(req_vo.create_time) == 2:
            stmt = stmt.where(
                SmsTemplateDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(SmsTemplateDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_count_by_channel_id(self, channel_id: int) -> int:
        stmt = select(func.count()).where(SmsTemplateDO.channel_id == channel_id)
        result = await self.read(stmt)
        return result.scalar_one()
