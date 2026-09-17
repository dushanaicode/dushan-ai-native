from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.sms.dto.code.code_sms_code_send_req_dto import SmsCodeSendReqDTO
from module_system.api.sms.dto.code.code_sms_code_use_req_dto import SmsCodeUseReqDTO
from module_system.api.sms.dto.code.code_sms_code_validate_req_dto import SmsCodeValidateReqDTO


@runtime_checkable
class SmsCodeApi(Protocol):
    """短信验证码API接口"""

    async def send_sms_code(self, req_dto: SmsCodeSendReqDTO) -> None:
        """创建并发送短信验证码"""
        ...

    async def use_sms_code(self, req_dto: SmsCodeUseReqDTO) -> None:
        """验证并使用短信验证码"""
        ...

    async def validate_sms_code(self, req_dto: SmsCodeValidateReqDTO) -> None:
        """检查验证码是否有效"""
        ...
