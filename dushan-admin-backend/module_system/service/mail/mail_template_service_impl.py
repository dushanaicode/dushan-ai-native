from __future__ import annotations

import re
from typing import override

from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.schemas.page_result import PageResult
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.decorators.cacheable import cache
from framework.starter_database.decorators.transactional import transactional
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.controller.admin.mail.vo.template.template_page_req_vo import (
    MailTemplatePageReqVO,
)
from module_system.controller.admin.mail.vo.template.template_save_req_vo import (
    MailTemplateSaveReqVO,
)
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.cache.mail.dto.mail_template_cache_dto import MailTemplateCacheDTO
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO
from module_system.dal.mapper.mail.mail_template_mapper import MailTemplateMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.mail.mail_template_service import MailTemplateService

_PATTERN_PARAMS = re.compile("\\{(.*?)}")


@service(interface=MailTemplateService)
class MailTemplateServiceImpl(MailTemplateService):
    """邮件模板服务。"""

    @override
    async def get_mail_template_by_code(self, code: str) -> MailTemplateDO | None:
        """发送校验读取当前事务内的数据，不使用缓存回源子任务。"""
        return await self.mail_template_mapper.select_by_code(code)

    cache_handler: CacheHandler = Inject()
    database: SessionProvider = Inject()
    mail_template_mapper: MailTemplateMapper = Inject()
    default_ttl: int = 3600

    @override
    @transactional
    async def create_mail_template(self, create_req_vo: MailTemplateSaveReqVO) -> int:
        await self._validate_code_unique(None, create_req_vo.code)
        template = MailTemplateDO(**create_req_vo.model_dump(by_alias=False))
        template.params = self.parse_template_content_params(create_req_vo.content)
        await self.mail_template_mapper.insert(template)
        return template.id

    @override
    @transactional
    async def update_mail_template(self, update_req_vo: MailTemplateSaveReqVO) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.MAIL_TEMPLATE),
            required=True,
            name="system-cache",
        )
        await self._validate_exists(update_req_vo.id)
        await self._validate_code_unique(update_req_vo.id, update_req_vo.code)
        update_obj = MailTemplateDO(**update_req_vo.model_dump(by_alias=False))
        update_obj.params = self.parse_template_content_params(update_req_vo.content)
        await self.mail_template_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, template_id: int, status: int) -> None:
        """更新邮件模板状态"""
        await self._validate_exists(template_id)
        update_obj = MailTemplateDO(id=template_id, status=status)
        await self.mail_template_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_mail_template(self, template_id: int) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.MAIL_TEMPLATE),
            required=True,
            name="system-cache",
        )
        await self._validate_exists(template_id)
        await self.mail_template_mapper.delete_by_id(template_id)

    @override
    @transactional
    async def delete_mail_template_batch(self, ids: list[int]) -> int:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.MAIL_TEMPLATE),
            required=True,
            name="system-cache",
        )
        templates = await self.mail_template_mapper.select_by_ids(ids)
        if len(templates) != len(ids):
            raise ServiceException(ErrorCodeConstants.MAIL_TEMPLATE_NOT_EXISTS)
        return await self.mail_template_mapper.delete_by_ids(ids)

    @override
    async def get_mail_template(self, id: int) -> MailTemplateDO:
        return await self.mail_template_mapper.select_by_id(id)

    @cache(
        SystemCacheKeys.MAIL_TEMPLATE,
        key="code:{{code}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: (
            not (result is not None and (not isinstance(result, Exception)))
        ),
    )
    @override
    async def get_mail_template_by_code_from_cache(self, code: str) -> MailTemplateCacheDTO | None:
        loaded = await self.mail_template_mapper.select_by_code(code)
        return None if loaded is None else MailTemplateCacheDTO.model_validate(loaded)

    @override
    async def get_mail_template_page(
        self, req_vo: MailTemplatePageReqVO
    ) -> PageResult[MailTemplateDO]:
        return await self.mail_template_mapper.select_page(req_vo)

    @override
    async def get_mail_template_list(self) -> list[MailTemplateDO]:
        return await self.mail_template_mapper.select_list()

    @override
    def format_mail_template_content(self, content: str, params: dict) -> str:
        return content.format_map(params)

    @override
    def parse_template_content_params(self, content: str) -> list[str]:
        return re.findall(_PATTERN_PARAMS, content)

    @override
    async def get_mail_template_count_by_account_id(self, account_id: int) -> int:
        return await self.mail_template_mapper.select_count_by_account_id(account_id)

    async def _validate_code_unique(self, id: int | None, code: str) -> None:
        """校验模板 code 是否唯一"""
        template = await self.mail_template_mapper.select_by_code(code)
        if template is None:
            return
        if id is None or id != template.id:
            raise ServiceException(ErrorCodeConstants.MAIL_TEMPLATE_CODE_EXISTS)

    async def _validate_exists(self, id: int) -> None:
        """校验邮件模板是否存在"""
        template = await self.mail_template_mapper.select_by_id(id)
        if template is None:
            raise ServiceException(ErrorCodeConstants.MAIL_TEMPLATE_NOT_EXISTS)
