from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.api.logger.dto.operate_log_create_req_dto import OperateLogCreateReqDTO
from module_system.api.logger.dto.operate_log_page_req_dto import OperateLogPageReqDTO
from module_system.api.logger.dto.operate_log_resp_dto import OperateLogRespDTO


@runtime_checkable
class OperateLogApi(Protocol):
    """操作日志API接口"""

    async def create_operate_log(self, req_dto: OperateLogCreateReqDTO) -> None:
        """创建操作日志"""
        ...

    async def get_operate_log_page(
        self, page_req_dto: OperateLogPageReqDTO
    ) -> PageResult[OperateLogRespDTO]:
        """获取操作日志分页"""
        ...
