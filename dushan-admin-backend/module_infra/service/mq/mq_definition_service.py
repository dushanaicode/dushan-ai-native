from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_infra.controller.admin.mq.vo.mq.mq_page_req_vo import MqPageReqVO
from module_infra.controller.admin.mq.vo.mq.mq_save_req_vo import MqSaveReqVO
from module_infra.dal.dataobject.mq.mq_do import MqDO


@runtime_checkable
class MqDefinitionService(Protocol):
    """MQ 消息定义服务接口"""

    async def create_mq_definition(self, create_req_vo: MqSaveReqVO) -> int:
        """创建消息定义"""
        ...

    async def update_mq_definition(self, update_req_vo: MqSaveReqVO) -> None:
        """更新消息定义"""
        ...

    async def delete_mq_definition(self, id: int) -> None:
        """删除消息定义"""
        ...

    async def get_mq_definition(self, id: int) -> MqDO | None:
        """根据ID获取消息定义信息"""
        ...

    async def get_mq_definition_page(self, page_req_vo: MqPageReqVO) -> PageResult[MqDO]:
        """分页查询消息定义"""
        ...

    async def get_mq_definition_list(
        self, topic: str | None = None, consumer: str | None = None
    ) -> list[MqDO]:
        """获取MQ消息定义列表"""
        ...
