from __future__ import annotations

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.mail.vo.account.account_page_req_vo import MailAccountPageReqVO
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO


@mapper()
class MailAccountMapper(BaseMapper[MailAccountDO]):
    def __init__(self):
        super().__init__(MailAccountDO)

    async def select_page(self, req_vo: MailAccountPageReqVO) -> PageResult[MailAccountDO]:
        stmt = select(MailAccountDO)
        if req_vo.mail:
            escaped_mail = StrUtils.escape_like(req_vo.mail)
            stmt = stmt.where(MailAccountDO.mail.ilike(f"%{escaped_mail}%"))
        if req_vo.username:
            escaped_user = StrUtils.escape_like(req_vo.username)
            stmt = stmt.where(MailAccountDO.username.ilike(f"%{escaped_user}%"))
        return await self.paginate_query(stmt, req_vo)

    async def exists(self, mail_account_id: int) -> bool:
        stmt = select(MailAccountDO).where(MailAccountDO.id == mail_account_id)
        result = await self.read(stmt)
        return result.scalar_one_or_none() is not None

    async def select_all(self) -> list[MailAccountDO]:
        stmt = select(MailAccountDO)
        result = await self.read(stmt)
        return list(result.scalars().all())
