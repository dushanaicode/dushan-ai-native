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
from module_system.controller.admin.mail.vo.template.template_page_req_vo import (
    MailTemplatePageReqVO,
)
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO


@mapper()
class MailTemplateMapper(BaseMapper[MailTemplateDO]):
    def __init__(self):
        super().__init__(MailTemplateDO)

    async def select_by_code(self, code: str) -> MailTemplateDO | None:
        stmt = select(MailTemplateDO).where(MailTemplateDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_page(self, req_vo: MailTemplatePageReqVO) -> PageResult[MailTemplateDO]:
        stmt = select(MailTemplateDO)
        if req_vo.status is not None:
            stmt = stmt.where(MailTemplateDO.status == req_vo.status)
        if req_vo.code:
            escaped_code = StrUtils.escape_like(req_vo.code)
            stmt = stmt.where(MailTemplateDO.code.ilike(f"%{escaped_code}%"))
        if req_vo.name:
            escaped_name = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(MailTemplateDO.name.ilike(f"%{escaped_name}%"))
        if req_vo.account_id is not None:
            stmt = stmt.where(MailTemplateDO.account_id == req_vo.account_id)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                MailTemplateDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(MailTemplateDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_count_by_account_id(self, account_id: int) -> int:
        stmt = select(func.count()).where(MailTemplateDO.account_id == account_id)
        result = await self.read(stmt)
        return result.scalar_one()

    async def select_list(self) -> list[MailTemplateDO]:
        stmt = select(MailTemplateDO)
        result = await self.read(stmt)
        return list(result.scalars().all())
