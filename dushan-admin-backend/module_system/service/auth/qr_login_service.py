from typing import Protocol, runtime_checkable

from module_system.controller.admin.auth.vo.auth_login_resp_vo import AuthLoginRespVO
from module_system.controller.admin.auth.vo.auth_qr_create_resp_vo import AuthQrCreateRespVO
from module_system.controller.admin.auth.vo.auth_qr_scan_resp_vo import AuthQrScanRespVO
from module_system.controller.admin.auth.vo.auth_qr_status_resp_vo import AuthQrStatusRespVO


@runtime_checkable
class QrLoginService(Protocol):
    async def create(self, binding: str, origin: str) -> AuthQrCreateRespVO: ...

    async def poll(self, token: str, binding: str, origin: str) -> AuthQrStatusRespVO: ...

    async def scan(self, token: str) -> AuthQrScanRespVO: ...

    async def confirm(self, token: str, approve: bool) -> None: ...

    async def cancel(self, token: str, binding: str, origin: str) -> None: ...

    async def consume(self, token: str, binding: str, origin: str) -> AuthLoginRespVO: ...
