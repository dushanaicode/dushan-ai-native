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
from module_infra.controller.admin.mq.vo.mq.mq_page_req_vo import MqPageReqVO
from module_infra.dal.dataobject.mq.mq_do import MqDO


@mapper()
class MqDefinitionMapper(BaseMapper[MqDO]):
    def __init__(self):
        super().__init__(MqDO)

    async def select_page(self, req_vo: MqPageReqVO) -> PageResult[MqDO]:
        """分页查询MQ消息定义"""
        stmt = select(MqDO)
        if req_vo.topic:
            escaped_topic = StrUtils.escape_like(req_vo.topic)
            stmt = stmt.where(MqDO.topic.ilike(f"%{escaped_topic}%"))
        if req_vo.consumer:
            escaped_consumer = StrUtils.escape_like(req_vo.consumer)
            stmt = stmt.where(MqDO.consumer.ilike(f"%{escaped_consumer}%"))
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                MqDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        return await self.paginate_query(stmt, req_vo)

    async def select_by_topic(self, topic: str) -> MqDO | None:
        """根据 Topic 查询消息定义"""
        stmt = select(MqDO).where(MqDO.topic == topic)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_consumer(self, consumer: str) -> MqDO | None:
        """根据消费者查询消息定义"""
        stmt = select(MqDO).where(MqDO.consumer == consumer)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list(
        self, topic: str | None = None, consumer: str | None = None
    ) -> list[MqDO]:
        """查询列表"""
        stmt = select(MqDO)
        if topic:
            stmt = stmt.where(MqDO.topic == topic)
        if consumer:
            stmt = stmt.where(MqDO.consumer == consumer)
        stmt = stmt.order_by(MqDO.id.desc())
        result = await self.read(stmt)
        return list(result.scalars().all())
