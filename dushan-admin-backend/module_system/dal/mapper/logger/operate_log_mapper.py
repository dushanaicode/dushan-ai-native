from __future__ import annotations

from sqlalchemy import select

from framework.common.page import PageQuery, PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.api.logger.dto.operate_log_page_req_dto import OperateLogPageReqDTO
from module_system.controller.admin.logger.vo.operatelog.operatelog_operate_log_page_req_vo import (
    OperateLogPageReqVO,
)
from module_system.dal.dataobject.logger.operate_log_do import OperateLogDO


@mapper()
class OperateLogMapper(BaseMapper[OperateLogDO]):
    def __init__(self):
        super().__init__(OperateLogDO)

    async def select_page_vo(self, req_vo: OperateLogPageReqVO) -> PageResult[OperateLogDO]:
        stmt = select(OperateLogDO)
        if req_vo.user_id is not None:
            stmt = stmt.where(OperateLogDO.user_id == req_vo.user_id)
        if req_vo.biz_id is not None:
            stmt = stmt.where(OperateLogDO.biz_id == req_vo.biz_id)
        if req_vo.type:
            escaped_type = StrUtils.escape_like(req_vo.type)
            stmt = stmt.where(OperateLogDO.type.ilike(f"%{escaped_type}%"))
        if req_vo.sub_type:
            escaped_sub = StrUtils.escape_like(req_vo.sub_type)
            stmt = stmt.where(OperateLogDO.sub_type.ilike(f"%{escaped_sub}%"))
        if req_vo.action:
            escaped_action = StrUtils.escape_like(req_vo.action)
            stmt = stmt.where(OperateLogDO.action.ilike(f"%{escaped_action}%"))
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                OperateLogDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(OperateLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_page_dto(self, req_dto: OperateLogPageReqDTO) -> PageResult[OperateLogDO]:
        stmt = select(OperateLogDO)
        if req_dto.type:
            stmt = stmt.where(OperateLogDO.type == req_dto.type)
        if req_dto.biz_id is not None:
            stmt = stmt.where(OperateLogDO.biz_id == req_dto.biz_id)
        if req_dto.user_id is not None:
            stmt = stmt.where(OperateLogDO.user_id == req_dto.user_id)
        stmt = stmt.order_by(OperateLogDO.id.desc())
        return await self.paginate_query(
            stmt, PageQuery(page=req_dto.page, page_size=req_dto.page_size)
        )
