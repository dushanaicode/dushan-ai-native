from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.logger.dto.login_log_create_req_dto import LoginLogCreateReqDTO
from module_system.api.logger.login_log_api import LoginLogApi
from module_system.service.logger.login_log_service import LoginLogService


@service(interface=LoginLogApi)
class LoginLogApiImpl(LoginLogApi):
    login_log_service: LoginLogService = Inject()

    @override
    async def create_login_log(self, req_dto: LoginLogCreateReqDTO) -> None:
        """创建登录日志"""
        await self.login_log_service.create_login_log(req_dto)
