from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.controller.admin.sms.vo.template.template_page_req_vo import SmsTemplatePageReqVO
from module_system.controller.admin.sms.vo.template.template_save_req_vo import SmsTemplateSaveReqVO
from module_system.dal.cache.sms.dto.sms_template_cache_dto import SmsTemplateCacheDTO
from module_system.dal.dataobject.sms.sms_template_do import SmsTemplateDO


@runtime_checkable
class SmsTemplateService(Protocol):
    async def get_sms_template_by_code(self, code: str) -> SmsTemplateDO | None: ...

    async def create_sms_template(self, create_req_vo: SmsTemplateSaveReqVO) -> int: ...

    async def update_sms_template(self, update_req_vo: SmsTemplateSaveReqVO) -> None: ...

    async def update_status(self, template_id: int, status: int) -> None: ...

    async def delete_sms_template(self, id: int) -> None: ...

    async def delete_sms_template_batch(self, ids: list[int]) -> int: ...

    async def get_sms_template(self, id: int) -> SmsTemplateDO: ...

    async def get_sms_template_by_code_from_cache(
        self, code: str
    ) -> SmsTemplateCacheDTO | None: ...

    async def get_sms_template_page(
        self, page_req_vo: SmsTemplatePageReqVO
    ) -> PageResult[SmsTemplateDO]: ...

    async def get_sms_template_count_by_channel_id(self, channel_id: int) -> int: ...

    async def get_sms_template_list(self) -> list[SmsTemplateDO]: ...

    def format_sms_template_content(self, content: str, params: dict[str, Any]) -> str: ...
