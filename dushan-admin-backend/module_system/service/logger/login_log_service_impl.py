from __future__ import annotations

from typing import override

from framework.common.page import PageResult
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.logger.dto.login_log_create_req_dto import LoginLogCreateReqDTO
from module_system.controller.admin.logger.vo.loginlog.loginlog_login_log_page_req_vo import (
    LoginLogPageReqVO,
)
from module_system.dal.dataobject.logger.login_log_do import LoginLogDO
from module_system.dal.mapper.logger.login_log_mapper import LoginLogMapper
from module_system.service.logger.login_log_service import LoginLogService


@service(interface=LoginLogService)
class LoginLogServiceImpl(LoginLogService):
    """登录日志服务实现类"""

    login_log_mapper: LoginLogMapper = Inject()

    @override
    async def get_login_log_page(self, req_vo: LoginLogPageReqVO) -> PageResult[LoginLogDO]:
        return await self.login_log_mapper.select_page(req_vo)

    @override
    @transactional
    async def create_login_log(self, req_dto: LoginLogCreateReqDTO) -> None:
        login_log = LoginLogDO(**req_dto.model_dump(by_alias=False))
        await self.login_log_mapper.insert(login_log)
