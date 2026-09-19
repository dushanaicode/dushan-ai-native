from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_infra.controller.admin.logger.vo.apierrorlog.apierrorlog_api_error_log_page_req_vo import (
    ApiErrorLogPageReqVO,
)
from module_infra.dal.dataobject.logger.api_error_log_do import ApiErrorLogDO


@mapper()
class ApiErrorLogMapper(BaseMapper[ApiErrorLogDO]):
    def __init__(self):
        super().__init__(ApiErrorLogDO)

    async def select_page(self, req_vo: ApiErrorLogPageReqVO) -> PageResult[ApiErrorLogDO]:
        """分页查询 API 错误日志"""
        stmt = select(ApiErrorLogDO)
        if req_vo.user_id is not None:
            stmt = stmt.where(ApiErrorLogDO.user_id == req_vo.user_id)
        if req_vo.user_type is not None:
            stmt = stmt.where(ApiErrorLogDO.user_type == req_vo.user_type)
        if req_vo.application_name:
            stmt = stmt.where(ApiErrorLogDO.application_name == req_vo.application_name)
        if req_vo.request_url:
            escaped = StrUtils.escape_like(req_vo.request_url)
            stmt = stmt.where(ApiErrorLogDO.request_url.ilike(f"%{escaped}%"))
        if req_vo.exception_time and len(req_vo.exception_time) >= 2:
            stmt = stmt.where(
                ApiErrorLogDO.exception_time.between(
                    req_vo.exception_time[0], req_vo.exception_time[1]
                )
            )
        if req_vo.process_status is not None:
            stmt = stmt.where(ApiErrorLogDO.process_status == req_vo.process_status)
        stmt = stmt.order_by(ApiErrorLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def delete_by_create_time_lt(self, create_time: datetime, limit: int) -> int:
        return await self.purge_limited_by_condition(
            ApiErrorLogDO.create_time < create_time, limit=limit
        )
