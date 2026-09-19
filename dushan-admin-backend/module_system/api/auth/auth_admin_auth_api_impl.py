from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.auth.auth_admin_auth_api import AuthAdminAuthApi
from module_system.service.auth.auth_admin_auth_service import AuthAdminAuthService


@service(interface=AuthAdminAuthApi)
class AuthAdminAuthApiImpl(AuthAdminAuthApi):
    admin_auth_service: AuthAdminAuthService = Inject()

    @override
    async def logout(self, token: str, log_type: int) -> None:
        """实现基于 token 的退出登录 API"""
        if not token:
            raise ValueError("token 不能为空")
        await self.admin_auth_service.logout(token, log_type)
