from __future__ import annotations

import re
from typing import Any, override

from framework.common.enums import BuiltinTypeEnum, StatusEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_cache.public import CacheHandler, cache
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.controller.admin.sms.vo.template.template_page_req_vo import SmsTemplatePageReqVO
from module_system.controller.admin.sms.vo.template.template_save_req_vo import SmsTemplateSaveReqVO
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.cache.sms.dto.sms_template_cache_dto import SmsTemplateCacheDTO
from module_system.dal.dataobject.sms.sms_channel_do import SmsChannelDO
from module_system.dal.dataobject.sms.sms_template_do import SmsTemplateDO
from module_system.dal.mapper.sms.sms_template_mapper import SmsTemplateMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.framework.sms.client.sms_client import SmsClient
from module_system.framework.sms.enums.sms_template_audit_status_enum import (
    SmsTemplateAuditStatusEnum,
)
from module_system.framework.sms.factory.sms_client_factory import SmsClientFactory
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties
from module_system.service.sms.sms_channel_service import SmsChannelService
from module_system.service.sms.sms_template_service import SmsTemplateService


@service(interface=SmsTemplateService)
class SmsTemplateServiceImpl(SmsTemplateService):
    @override
    async def get_sms_template_by_code(self, code: str) -> SmsTemplateDO | None:
        """发送校验读取当前事务内的数据，不使用缓存回源子任务。"""
        return await self.sms_template_mapper.select_by_code(code)

    cache_handler: CacheHandler = Inject()
    database: SessionProvider = Inject()
    sms_client_factory: SmsClientFactory = Inject()
    sms_template_mapper: SmsTemplateMapper = Inject()
    sms_channel_service: SmsChannelService = Inject()
    default_ttl: int = 3600

    @override
    @transactional
    async def create_sms_template(self, create_req_vo: SmsTemplateSaveReqVO) -> int:
        channel_do: SmsChannelDO = await self._validate_sms_channel(create_req_vo.channel_id)
        await self._validate_sms_template_code_duplicate(None, create_req_vo.code)
        await self._validate_api_template(create_req_vo.channel_id, create_req_vo.api_template_id)
        template = SmsTemplateDO(**create_req_vo.model_dump(by_alias=False))
        template.params = self._parse_template_content_params(template.content)
        template.channel_code = channel_do.code
        await self.sms_template_mapper.insert(template)
        return template.id

    @override
    @transactional
    async def update_sms_template(self, update_req_vo: SmsTemplateSaveReqVO) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.SMS_TEMPLATE),
            required=True,
            name="system-cache",
        )
        await self._validate_for_update(update_req_vo.id)
        channel_do: SmsChannelDO = await self._validate_sms_channel(update_req_vo.channel_id)
        await self._validate_sms_template_code_duplicate(update_req_vo.id, update_req_vo.code)
        await self._validate_api_template(update_req_vo.channel_id, update_req_vo.api_template_id)
        update_obj = SmsTemplateDO(**update_req_vo.model_dump(by_alias=False))
        update_obj.params = self._parse_template_content_params(update_obj.content)
        update_obj.channel_code = channel_do.code
        await self.sms_template_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, template_id: int, status: int) -> None:
        """更新短信模板状态"""
        await self._validate_for_update(template_id)
        update_obj = SmsTemplateDO(id=template_id, status=status)
        await self.sms_template_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_sms_template(self, id: int) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.SMS_TEMPLATE),
            required=True,
            name="system-cache",
        )
        await self._validate_for_update(id)
        await self.sms_template_mapper.delete_by_id(id)

    @override
    @transactional
    async def delete_sms_template_batch(self, ids: list[int]) -> int:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.SMS_TEMPLATE),
            required=True,
            name="system-cache",
        )
        for template_id in ids:
            await self._validate_for_update(template_id)
        return await self.sms_template_mapper.delete_by_ids(ids)

    @override
    async def get_sms_template(self, id: int) -> SmsTemplateDO:
        return await self.sms_template_mapper.select_by_id(id)

    @cache(
        SystemCacheKeys.SMS_TEMPLATE,
        key="code:{{code}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: not result is not None,
    )
    @override
    async def get_sms_template_by_code_from_cache(self, code: str) -> SmsTemplateCacheDTO | None:
        loaded = await self.sms_template_mapper.select_by_code(code)
        return None if loaded is None else SmsTemplateCacheDTO.model_validate(loaded)

    @override
    async def get_sms_template_page(
        self, page_req_vo: SmsTemplatePageReqVO
    ) -> PageResult[SmsTemplateDO]:
        return await self.sms_template_mapper.select_page(page_req_vo)

    @override
    async def get_sms_template_count_by_channel_id(self, channel_id: int) -> int:
        return await self.sms_template_mapper.select_count_by_channel_id(channel_id)

    @override
    async def get_sms_template_list(self) -> list[SmsTemplateDO]:
        return await self.sms_template_mapper.select_list()

    @override
    def format_sms_template_content(self, content: str, params: dict[str, Any]) -> str:
        return content.format(**params)

    def _parse_template_content_params(self, content: str) -> list[str]:
        """解析模板内容中 {} 内的变量名"""
        pattern = re.compile("\\{(.*?)}")
        return re.findall(pattern, content)

    async def _validate_for_update(self, id: int | None) -> None:
        """校验模板是否存在且非内置"""
        if id is None:
            raise ServiceException(ErrorCodeConstants.SMS_TEMPLATE_NOT_EXISTS)
        template = await self.sms_template_mapper.select_by_id(id)
        if template is None:
            raise ServiceException(ErrorCodeConstants.SMS_TEMPLATE_NOT_EXISTS)
        if template.builtin == BuiltinTypeEnum.BUILTIN.code:
            raise ServiceException(ErrorCodeConstants.SMS_TEMPLATE_CAN_NOT_UPDATE_BUILTIN)

    async def _validate_sms_template_code_duplicate(self, id: int | None, code: str) -> None:
        template = await self.sms_template_mapper.select_by_code(code)
        if template is None:
            return
        if id is None or template.id != id:
            raise ServiceException(ErrorCodeConstants.SMS_TEMPLATE_CODE_DUPLICATE, code)

    async def _validate_sms_channel(self, channel_id: int) -> SmsChannelDO:
        channel = await self.sms_channel_service.get_sms_channel(channel_id)
        if channel is None:
            raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_NOT_EXISTS)
        if channel.status != StatusEnum.ENABLE.code:
            raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_DISABLE)
        return channel

    async def _validate_api_template(self, channel_id: int, api_template_id: str) -> None:
        channel_do = await self.sms_channel_service.get_sms_channel(channel_id)
        if channel_do is None:
            raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_NOT_EXISTS)
        properties = SmsChannelProperties.model_validate(channel_do)
        sms_client: SmsClient = self.sms_client_factory.create_or_update_sms_client(properties)
        if sms_client is None:
            raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_NOT_EXISTS)
        try:
            template_resp = await sms_client.get_sms_template(api_template_id)
        except Exception as ex:
            raise ServiceException(ErrorCodeConstants.SMS_TEMPLATE_API_ERROR, str(ex))
        if template_resp is None:
            raise ServiceException(ErrorCodeConstants.SMS_TEMPLATE_API_NOT_FOUND)
        if template_resp.audit_status == SmsTemplateAuditStatusEnum.CHECKING.code:
            raise ServiceException(ErrorCodeConstants.SMS_TEMPLATE_API_AUDIT_CHECKING)
        if template_resp.audit_status == SmsTemplateAuditStatusEnum.FAIL.code:
            raise ServiceException(
                ErrorCodeConstants.SMS_TEMPLATE_API_AUDIT_FAIL, template_resp.audit_reason
            )
        if template_resp.audit_status != SmsTemplateAuditStatusEnum.SUCCESS.code:
            raise ServiceException(
                ErrorCodeConstants.SMS_TEMPLATE_API_AUDIT_UNKNOWN,
                api_template_id,
                template_resp.audit_status,
            )
