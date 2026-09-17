from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.controller.admin.mail.vo.template.template_page_req_vo import (
    MailTemplatePageReqVO,
)
from module_system.controller.admin.mail.vo.template.template_save_req_vo import (
    MailTemplateSaveReqVO,
)
from module_system.dal.cache.mail.dto.mail_template_cache_dto import MailTemplateCacheDTO
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO


@runtime_checkable
class MailTemplateService(Protocol):
    async def get_mail_template_by_code(self, code: str) -> MailTemplateDO | None: ...

    async def create_mail_template(self, create_req_vo: MailTemplateSaveReqVO) -> int: ...

    async def update_mail_template(self, update_req_vo: MailTemplateSaveReqVO) -> None: ...

    async def update_status(self, template_id: int, status: int) -> None: ...

    async def delete_mail_template(self, template_id: int) -> None: ...

    async def delete_mail_template_batch(self, ids: list[int]) -> int: ...

    async def get_mail_template(self, id: int) -> MailTemplateDO: ...

    async def get_mail_template_by_code_from_cache(
        self, code: str
    ) -> MailTemplateCacheDTO | None: ...

    async def get_mail_template_page(
        self, req_vo: MailTemplatePageReqVO
    ) -> PageResult[MailTemplateDO]: ...

    async def get_mail_template_list(self) -> list[MailTemplateDO]: ...

    def format_mail_template_content(self, content: str, params: dict) -> str: ...

    def parse_template_content_params(self, content: str) -> list[str]: ...

    async def get_mail_template_count_by_account_id(self, account_id: int) -> int: ...
