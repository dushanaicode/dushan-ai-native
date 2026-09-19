from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import override

from framework.common.page import PageResult
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    MessageState,
)
from module_infra.controller.admin.mq.vo.log.log_page_req_vo import MqLogPageReqVO
from module_infra.dal.dataobject.mq.mq_log_do import MqLogDO
from module_infra.dal.mapper.mq.mq_log_mapper import MqLogMapper
from module_infra.service.mq.mq_log_service import MqLogService


@service(interface=MqLogService)
class MqLogServiceImpl(MqLogService):
    mq_log_mapper: MqLogMapper = Inject()

    @override
    async def get_log(self, log_id: int) -> MqLogDO | None:
        return await self.mq_log_mapper.select_by_id(log_id)

    @override
    async def get_log_page(self, page_req_vo: MqLogPageReqVO) -> PageResult[MqLogDO]:
        return await self.mq_log_mapper.select_page(page_req_vo)

    async def record(self, record):
        finished = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.mq_log_mapper.insert(
            MqLogDO(
                message_id=record.context.message_id,
                topic=record.context.destination,
                consumer=record.context.consumer_key,
                execute_index=record.context.attempt,
                begin_time=finished - timedelta(seconds=record.elapsed_seconds),
                end_time=finished,
                duration=int(record.elapsed_seconds * 1000),
                status=1 if record.state is MessageState.SUCCEEDED else 2,
                state=record.state.code,
                result=record.error_type,
                payload=None,
            )
        )
