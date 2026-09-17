from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.logger.dto.login_log_create_req_dto import LoginLogCreateReqDTO


@runtime_checkable
class LoginLogApi(Protocol):
    """登录日志API接口"""

    async def create_login_log(self, req_dto: LoginLogCreateReqDTO) -> None:
        """创建登录日志"""
        ...
