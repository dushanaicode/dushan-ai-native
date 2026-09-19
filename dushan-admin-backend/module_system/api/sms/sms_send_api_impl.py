from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.sms.dto.send.send_sms_send_single_to_user_req_dto import (
    SmsSendSingleToUserReqDTO,
)
from module_system.api.sms.sms_send_api import SmsSendApi
from module_system.service.sms.bo.sms_send_bo import SmsSendBO
from module_system.service.sms.sms_send_service import SmsSendService


@service(interface=SmsSendApi)
class SmsSendApiImpl(SmsSendApi):
    sms_send_service: SmsSendService = Inject()

    @override
    async def send_single_sms_to_admin(self, req_dto: SmsSendSingleToUserReqDTO) -> int:
        """向管理员用户发送单条短信"""
        return await self.sms_send_service.send_single_sms_to_admin(
            SmsSendBO(
                mobile=req_dto.mobile,
                user_id=req_dto.user_id,
                template_code=req_dto.template_code,
                template_params=req_dto.template_params,
            )
        )

    @override
    async def send_single_sms_to_member(self, req_dto: SmsSendSingleToUserReqDTO) -> int:
        """向会员用户发送单条短信"""
        return await self.sms_send_service.send_single_sms_to_member(
            SmsSendBO(
                mobile=req_dto.mobile,
                user_id=req_dto.user_id,
                template_code=req_dto.template_code,
                template_params=req_dto.template_params,
            )
        )
