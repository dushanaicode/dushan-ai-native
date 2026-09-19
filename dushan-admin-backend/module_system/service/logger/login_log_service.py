from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.api.logger.dto.login_log_create_req_dto import LoginLogCreateReqDTO
from module_system.controller.admin.logger.vo.loginlog.loginlog_login_log_page_req_vo import (
    LoginLogPageReqVO,
)
from module_system.dal.dataobject.logger.login_log_do import LoginLogDO


@runtime_checkable
class LoginLogService(Protocol):
    async def get_login_log_page(self, req_vo: LoginLogPageReqVO) -> PageResult[LoginLogDO]: ...

    async def create_login_log(self, req_dto: LoginLogCreateReqDTO) -> None: ...
