from __future__ import annotations

from sqlalchemy import select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.logger.vo.login_log.login_log_page_req_vo import (
    LoginLogPageReqVO,
)
from module_system.dal.dataobject.logger.login_log_do import LoginLogDO


@mapper()
class LoginLogMapper(BaseMapper[LoginLogDO]):
    def __init__(self):
        super().__init__(LoginLogDO)

    async def select_page(self, req_vo: LoginLogPageReqVO) -> PageResult[LoginLogDO]:
        stmt = select(LoginLogDO)
        if req_vo.user_ip:
            escaped_ip = StrUtils.escape_like(req_vo.user_ip)
            stmt = stmt.where(LoginLogDO.user_ip.ilike(f"%{escaped_ip}%", escape="\\"))
        if req_vo.username:
            escaped_user = StrUtils.escape_like(req_vo.username)
            stmt = stmt.where(LoginLogDO.username.ilike(f"%{escaped_user}%", escape="\\"))
        if req_vo.create_time is not None:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(LoginLogDO.create_time.between(start_time, end_time))
        if req_vo.result is not None:
            stmt = stmt.where(LoginLogDO.result == req_vo.result)
        if req_vo.log_type is not None:
            stmt = stmt.where(LoginLogDO.log_type == req_vo.log_type)
        stmt = stmt.order_by(LoginLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)
