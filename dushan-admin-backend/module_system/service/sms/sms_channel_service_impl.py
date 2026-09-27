from __future__ import annotations

from typing import override

from framework.common.exception import IllegalArgumentException, ServiceException
from framework.common.page import PageResult
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.config.system_settings import SystemSettings
from module_system.controller.admin.sms.vo.channel.channel_page_req_vo import SmsChannelPageReqVO
from module_system.controller.admin.sms.vo.channel.channel_save_req_vo import SmsChannelSaveReqVO
from module_system.dal.dataobject.sms.sms_channel_do import SmsChannelDO
from module_system.dal.mapper.sms.sms_channel_mapper import SmsChannelMapper
from module_system.dal.mapper.sms.sms_template_mapper import SmsTemplateMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.framework.sms.sms_callback_token import SmsCallbackToken
from module_system.service.sms.sms_channel_service import SmsChannelService


@service(interface=SmsChannelService)
class SmsChannelServiceImpl(SmsChannelService):
    settings: SystemSettings = Inject()
    sms_channel_mapper: SmsChannelMapper = Inject()
    sms_template_mapper: SmsTemplateMapper = Inject()

    async def get_callback_token(self, channel_id: int) -> str:
        channel = await self._validate_sms_channel_exists(channel_id)
        return SmsCallbackToken.create(
            self.settings.sms_callback_token, channel.tenant_id, channel.id
        )

    @override
    @transactional
    async def create_sms_channel(self, create_req_vo: SmsChannelSaveReqVO) -> int:
        if create_req_vo.id is not None:
            raise IllegalArgumentException(msg="新增短信渠道不能指定编号")
        channel = SmsChannelDO(**create_req_vo.model_dump(by_alias=False))
        await self.sms_channel_mapper.insert(channel)
        return channel.id

    @override
    @transactional
    async def update_sms_channel(self, update_req_vo: SmsChannelSaveReqVO) -> None:
        channel = await self._validate_sms_channel_exists(update_req_vo.id)
        if channel.code != update_req_vo.code:
            raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_CODE_IMMUTABLE)
        values = update_req_vo.model_dump(by_alias=False)
        for field in ("api_key", "api_secret"):
            if values[field] is None:
                values.pop(field)
        update_obj = SmsChannelDO(**values)
        await self.sms_channel_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, channel_id: int, status: int) -> None:
        """更新短信渠道状态"""
        await self._validate_sms_channel_exists(channel_id)
        update_obj = SmsChannelDO(id=channel_id, status=status)
        await self.sms_channel_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_sms_channel(self, sms_channel_id: int) -> None:
        await self._validate_sms_channel_exists(sms_channel_id)
        count = await self.sms_template_mapper.select_count_by_channel_id(sms_channel_id)
        if count > 0:
            raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_HAS_CHILDREN)
        await self.sms_channel_mapper.delete_by_id(sms_channel_id)

    @override
    @transactional
    async def delete_sms_channel_batch(self, ids: list[int]) -> int:
        for channel_id in ids:
            await self._validate_sms_channel_exists(channel_id)
            template_count = await self.sms_template_mapper.select_count_by_channel_id(channel_id)
            if template_count > 0:
                channel = await self.sms_channel_mapper.select_by_id(channel_id)
                raise ServiceException(
                    ErrorCodeConstants.SMS_CHANNEL_HAS_CHILDREN, channel.signature
                )
        return await self.sms_channel_mapper.delete_by_ids(ids)

    @override
    async def get_sms_channel(self, sms_channel_id: int) -> SmsChannelDO | None:
        return await self.sms_channel_mapper.select_by_id(sms_channel_id)

    @override
    async def get_sms_channel_list(self) -> list[SmsChannelDO]:
        return await self.sms_channel_mapper.select_list()

    @override
    async def get_sms_channel_page(
        self, page_req_vo: SmsChannelPageReqVO
    ) -> PageResult[SmsChannelDO]:
        return await self.sms_channel_mapper.select_page(page_req_vo)

    async def _validate_sms_channel_exists(self, sms_channel_id: int) -> SmsChannelDO:
        channel = await self.sms_channel_mapper.select_by_id(sms_channel_id)
        if channel is None:
            raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_NOT_EXISTS)
        return channel
