from __future__ import annotations

from typing import override

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.sms.dto.code.code_sms_code_send_req_dto import SmsCodeSendReqDTO
from module_system.api.sms.dto.code.code_sms_code_use_req_dto import SmsCodeUseReqDTO
from module_system.api.sms.dto.code.code_sms_code_validate_req_dto import SmsCodeValidateReqDTO
from module_system.api.sms.sms_code_api import SmsCodeApi
from module_system.service.sms.sms_code_service import SmsCodeService


@service(interface=SmsCodeApi)
class SmsCodeApiImpl(SmsCodeApi):
    sms_code_service: SmsCodeService = Inject()

    @override
    async def send_sms_code(self, req_dto: SmsCodeSendReqDTO) -> None:
        """创建并发送短信验证码"""
        await self.sms_code_service.send_sms_code(req_dto)

    @override
    async def use_sms_code(self, req_dto: SmsCodeUseReqDTO) -> None:
        """验证并使用短信验证码"""
        await self.sms_code_service.use_sms_code(req_dto)

    @override
    async def validate_sms_code(self, req_dto: SmsCodeValidateReqDTO) -> None:
        """检查验证码是否有效"""
        await self.sms_code_service.validate_sms_code(req_dto)
