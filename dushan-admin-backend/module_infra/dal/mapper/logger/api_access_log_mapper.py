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
from module_infra.controller.admin.logger.vo.api_access_log.api_access_log_page_req_vo import (
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
            stmt = stmt.where(ApiAccessLogDO.request_url.ilike(f"%{escaped}%", escape="\\"))
        if req_vo.begin_time is not None:
            start_time, end_time = req_vo.begin_time
            stmt = stmt.where(ApiAccessLogDO.begin_time.between(start_time, end_time))
        if req_vo.duration is not None:
            stmt = stmt.where(ApiAccessLogDO.duration >= req_vo.duration)
        if req_vo.result_code is not None:
            stmt = stmt.where(ApiAccessLogDO.result_code == req_vo.result_code)
        stmt = stmt.order_by(ApiAccessLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def delete_by_create_time_lt(self, create_time: datetime, limit: int) -> int:
        """按每批上限清理到期访问日志，返回累计条数。"""
        return await self.purge_in_batches_by_condition(
            ApiAccessLogDO.create_time < create_time, limit=limit
        )
