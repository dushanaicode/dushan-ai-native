from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.sms.dto.send.send_sms_send_single_to_user_req_dto import (
    SmsSendSingleToUserReqDTO,
)


@runtime_checkable
class SmsSendApi(Protocol):
    """短信发送API接口"""

    async def send_single_sms_to_admin(self, req_dto: SmsSendSingleToUserReqDTO) -> int:
        """向管理员用户发送单条短信"""
        ...

    async def send_single_sms_to_member(self, req_dto: SmsSendSingleToUserReqDTO) -> int:
        """向会员用户发送单条短信"""
        ...
