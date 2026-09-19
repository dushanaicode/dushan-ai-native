from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.controller.admin.sms.vo.channel.channel_page_req_vo import SmsChannelPageReqVO
from module_system.controller.admin.sms.vo.channel.channel_save_req_vo import SmsChannelSaveReqVO
from module_system.dal.dataobject.sms.sms_channel_do import SmsChannelDO
from module_system.framework.sms.client.sms_client import SmsClient


@runtime_checkable
class SmsChannelService(Protocol):
    async def create_sms_channel(self, create_req_vo: SmsChannelSaveReqVO) -> int: ...

    async def update_sms_channel(self, update_req_vo: SmsChannelSaveReqVO) -> None: ...

    async def update_status(self, channel_id: int, status: int) -> None: ...

    async def delete_sms_channel(self, sms_channel_id: int) -> None: ...

    async def delete_sms_channel_batch(self, ids: list[int]) -> int: ...

    async def get_sms_channel(self, sms_channel_id: int) -> SmsChannelDO: ...

    async def get_sms_channel_list(self) -> list[SmsChannelDO]: ...

    async def get_sms_channel_page(
        self, page_req_vo: SmsChannelPageReqVO
    ) -> PageResult[SmsChannelDO]: ...

    async def get_sms_client_by_code(self, code: str) -> SmsClient: ...
