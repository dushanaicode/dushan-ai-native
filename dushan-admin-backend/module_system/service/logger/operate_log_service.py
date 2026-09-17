from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.api.logger.dto.operate_log_create_req_dto import OperateLogCreateReqDTO
from module_system.api.logger.dto.operate_log_page_req_dto import OperateLogPageReqDTO
from module_system.controller.admin.logger.vo.operatelog.operatelog_operate_log_page_req_vo import (
    OperateLogPageReqVO,
)
from module_system.dal.dataobject.logger.operate_log_do import OperateLogDO


@runtime_checkable
class OperateLogService(Protocol):
    async def create_operate_log(self, req_dto: OperateLogCreateReqDTO) -> None: ...

    async def get_operate_log_page_vo(
        self, req: OperateLogPageReqVO
    ) -> PageResult[OperateLogDO]: ...

    async def get_operate_log_page_dto(
        self, req: OperateLogPageReqDTO
    ) -> PageResult[OperateLogDO]: ...

    async def reserve(self, operation): ...

    async def finalize(self, reservation, entry): ...

    async def renew(self, reservation): ...

    async def cancel(self, reservation): ...
