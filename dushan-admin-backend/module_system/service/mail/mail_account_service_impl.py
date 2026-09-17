from __future__ import annotations

from typing import override

from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.schemas.page_result import PageResult
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.decorators.cacheable import cache
from framework.starter_database.decorators.transactional import transactional
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.controller.admin.mail.vo.account.account_page_req_vo import MailAccountPageReqVO
from module_system.controller.admin.mail.vo.account.account_save_req_vo import MailAccountSaveReqVO
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.cache.mail.dto.mail_account_cache_dto import MailAccountCacheDTO
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.dal.mapper.mail.mail_account_mapper import MailAccountMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.mail.mail_account_service import MailAccountService
from module_system.service.mail.mail_template_service import MailTemplateService


@service(interface=MailAccountService)
class MailAccountServiceImpl(MailAccountService):
    cache_handler: CacheHandler = Inject()
    database: SessionProvider = Inject()
    "邮箱账号服务实现类"
    mail_account_mapper: MailAccountMapper = Inject()
    mail_template_service: MailTemplateService = Inject()
    default_ttl: int = 3600

    @override
    @transactional
    async def create_mail_account(self, create_req_vo: MailAccountSaveReqVO) -> int:
        account = MailAccountDO(**create_req_vo.model_dump(by_alias=False))
        await self.mail_account_mapper.insert(account)
        return account.id

    @override
    @transactional
    async def update_mail_account(self, update_req_vo: MailAccountSaveReqVO) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.MAIL_ACCOUNT),
            required=True,
            name="system-cache",
        )
        await self._validate_exists(update_req_vo.id)
        update_obj = MailAccountDO(**update_req_vo.model_dump(by_alias=False))
        await self.mail_account_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_mail_account(self, id: int) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.MAIL_ACCOUNT),
            required=True,
            name="system-cache",
        )
        await self._validate_exists(id)
        if await self.mail_template_service.get_mail_template_count_by_account_id(id) > 0:
            raise ServiceException(ErrorCodeConstants.MAIL_ACCOUNT_RELATE_TEMPLATE_EXISTS)
        await self.mail_account_mapper.delete_by_id(id)

    @override
    @transactional
    async def delete_mail_account_batch(self, ids: list[int]) -> int:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.MAIL_ACCOUNT),
            required=True,
            name="system-cache",
        )
        accounts = await self.mail_account_mapper.select_by_ids(ids)
        if len(accounts) != len(ids):
            raise ServiceException(ErrorCodeConstants.MAIL_ACCOUNT_NOT_EXISTS)
        for account_id in ids:
            if (
                await self.mail_template_service.get_mail_template_count_by_account_id(account_id)
                > 0
            ):
                raise ServiceException(ErrorCodeConstants.MAIL_ACCOUNT_RELATE_TEMPLATE_EXISTS)
        return await self.mail_account_mapper.delete_by_ids(ids)

    @override
    async def get_mail_account(self, id: int) -> MailAccountDO | None:
        return await self.mail_account_mapper.select_by_id(id)

    @cache(
        SystemCacheKeys.MAIL_ACCOUNT,
        key="id:{{id}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: (
            not (result is not None and (not isinstance(result, Exception)))
        ),
    )
    @override
    async def get_mail_account_from_cache(self, id: int) -> MailAccountCacheDTO | None:
        loaded = await self.get_mail_account(id)
        return None if loaded is None else MailAccountCacheDTO.model_validate(loaded)

    @override
    async def get_mail_account_page(
        self, page_req_vo: MailAccountPageReqVO
    ) -> PageResult[MailAccountDO]:
        return await self.mail_account_mapper.select_page(page_req_vo)

    @override
    async def get_mail_account_list(self) -> list[MailAccountDO]:
        return await self.mail_account_mapper.select_all()

    async def _validate_exists(self, id: int) -> None:
        """校验邮箱账号是否存在"""
        if await self.mail_account_mapper.select_by_id(id) is None:
            raise ServiceException(ErrorCodeConstants.MAIL_ACCOUNT_NOT_EXISTS)
