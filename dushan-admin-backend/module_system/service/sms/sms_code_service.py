from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SmsCodeService(Protocol):
    async def send_sms_code(self, req_dto) -> None: ...

    async def use_sms_code(self, req_dto) -> None: ...

    async def validate_sms_code(self, req_dto) -> None: ...
