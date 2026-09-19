from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.controller.admin.mail.vo.account.account_page_req_vo import MailAccountPageReqVO
from module_system.controller.admin.mail.vo.account.account_save_req_vo import MailAccountSaveReqVO
from module_system.dal.cache.mail.dto.mail_account_cache_dto import MailAccountCacheDTO
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO


@runtime_checkable
class MailAccountService(Protocol):
    async def create_mail_account(self, create_req_vo: MailAccountSaveReqVO) -> int: ...

    async def update_mail_account(self, update_req_vo: MailAccountSaveReqVO) -> None: ...

    async def delete_mail_account(self, id: int) -> None: ...

    async def delete_mail_account_batch(self, ids: list[int]) -> int: ...

    async def get_mail_account(self, id: int) -> MailAccountDO | None: ...

    async def get_mail_account_from_cache(self, id: int) -> MailAccountCacheDTO | None: ...

    async def get_mail_account_page(
        self, page_req_vo: MailAccountPageReqVO
    ) -> PageResult[MailAccountDO]: ...

    async def get_mail_account_list(self) -> list[MailAccountDO]: ...
