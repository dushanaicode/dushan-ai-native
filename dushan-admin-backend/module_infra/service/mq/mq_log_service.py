from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_infra.controller.admin.mq.vo.log.log_page_req_vo import MqLogPageReqVO
from module_infra.dal.dataobject.mq.mq_log_do import MqLogDO


@runtime_checkable
class MqLogService(Protocol):
    """MQ 消费日志服务接口"""

    async def get_log(self, log_id: int) -> MqLogDO | None:
        """根据ID获取消费日志信息"""
        ...

    async def get_log_page(self, page_req_vo: MqLogPageReqVO) -> PageResult[MqLogDO]:
        """分页查询消费日志"""
        ...

    async def record(self, record): ...
