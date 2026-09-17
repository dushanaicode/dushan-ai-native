from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.controller.admin.auth.vo.auth_bind_mobile_req_vo import AuthBindMobileReqVO
from module_system.controller.admin.auth.vo.auth_login_req_vo import AuthLoginReqVO
from module_system.controller.admin.auth.vo.auth_login_resp_vo import AuthLoginRespVO
from module_system.controller.admin.auth.vo.auth_permission_info_resp_vo import (
    AuthPermissionInfoRespVO,
)
from module_system.controller.admin.auth.vo.auth_register_req_vo import AuthRegisterReqVO
from module_system.controller.admin.auth.vo.auth_reset_password_req_vo import AuthResetPasswordReqVO
from module_system.controller.admin.auth.vo.auth_sms_login_req_vo import AuthSmsLoginReqVO
from module_system.controller.admin.auth.vo.auth_sms_send_req_vo import AuthSmsSendReqVO
from module_system.controller.admin.auth.vo.auth_social_login_req_vo import AuthSocialLoginReqVO


@runtime_checkable
class AuthAdminAuthService(Protocol):
    async def login(self, req_vo: AuthLoginReqVO) -> AuthLoginRespVO: ...

    async def send_sms_code(self, req_vo: AuthSmsSendReqVO) -> None: ...

    async def sms_login(self, req_vo: AuthSmsLoginReqVO) -> AuthLoginRespVO: ...

    async def bind_mobile(self, user_id: int, req_vo: AuthBindMobileReqVO) -> None: ...

    async def social_login(self, req_vo: AuthSocialLoginReqVO) -> AuthLoginRespVO: ...

    async def refresh_token(self, refresh_token: str, client_id: str) -> AuthLoginRespVO: ...

    async def logout(self, token: str, log_type: int) -> None: ...

    async def register(self, req: AuthRegisterReqVO) -> AuthLoginRespVO: ...

    async def reset_password(self, req: AuthResetPasswordReqVO) -> None: ...

    async def get_permission_info(self, user_id: int) -> AuthPermissionInfoRespVO | None: ...

    async def authenticate(self, username: str, password: str): ...
