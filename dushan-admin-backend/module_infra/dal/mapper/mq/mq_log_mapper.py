from __future__ import annotations

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_infra.controller.admin.mq.vo.log.log_page_req_vo import MqLogPageReqVO
from module_infra.dal.dataobject.mq.mq_log_do import MqLogDO


@mapper()
class MqLogMapper(BaseMapper[MqLogDO]):
    def __init__(self):
        super().__init__(MqLogDO)

    async def select_page(self, req_vo: MqLogPageReqVO) -> PageResult[MqLogDO]:
        """分页查询MQ消息日志"""
        stmt = select(MqLogDO)
        if req_vo.message_id:
            stmt = stmt.where(MqLogDO.message_id == req_vo.message_id)
        if req_vo.consumer:
            stmt = stmt.where(MqLogDO.consumer == req_vo.consumer)
        if req_vo.begin_time:
            stmt = stmt.where(MqLogDO.begin_time >= req_vo.begin_time)
        if req_vo.end_time:
            stmt = stmt.where(MqLogDO.end_time <= req_vo.end_time)
        if req_vo.status is not None:
            stmt = stmt.where(MqLogDO.status == req_vo.status)
        stmt = stmt.order_by(MqLogDO.id.desc())
        return await self.paginate_query(stmt, req_vo)
