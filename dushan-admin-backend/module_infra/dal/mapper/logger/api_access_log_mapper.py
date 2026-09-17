from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_infra.controller.admin.logger.vo.apiaccesslog.apiaccesslog_api_access_log_page_req_vo import (
    ApiAccessLogPageReqVO,
)
from module_infra.dal.dataobject.logger.api_access_log_do import ApiAccessLogDO


@mapper()
class ApiAccessLogMapper(BaseMapper[ApiAccessLogDO]):
    def __init__(self):
        super().__init__(ApiAccessLogDO)

    async def select_page(self, req_vo: ApiAccessLogPageReqVO) -> PageResult[ApiAccessLogDO]:
        """分页查询 API 访问日志"""
        stmt = select(ApiAccessLogDO)
        if req_vo.user_id is not None:
            stmt = stmt.where(ApiAccessLogDO.user_id == req_vo.user_id)
        if req_vo.user_type is not None:
            stmt = stmt.where(ApiAccessLogDO.user_type == req_vo.user_type)
        if req_vo.application_name:
            stmt = stmt.where(ApiAccessLogDO.application_name == req_vo.application_name)
        if req_vo.request_url:
            escaped = StrUtils.escape_like(req_vo.request_url)
            stmt = stmt.where(ApiAccessLogDO.request_url.ilike(f"%{escaped}%"))
        if req_vo.begin_time and len(req_vo.begin_time) >= 2:
            stmt = stmt.where(
                ApiAccessLogDO.create_time.between(req_vo.begin_time[0], req_vo.begin_time[1])
            )
        if req_vo.duration is not None:
            stmt = stmt.where(ApiAccessLogDO.duration >= req_vo.duration)
        if req_vo.result_code is not None:
            stmt = stmt.where(ApiAccessLogDO.result_code == req_vo.result_code)
        stmt = stmt.order_by(ApiAccessLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def delete_by_create_time_lt(self, create_time: datetime, limit: int) -> int:
        return await self.purge_limited_by_condition(
            ApiAccessLogDO.create_time < create_time, limit=limit
        )
