from __future__ import annotations

from typing import override

from framework.common.page.schemas.page_result import PageResult
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.logger.dto.operate_log_create_req_dto import OperateLogCreateReqDTO
from module_system.api.logger.dto.operate_log_page_req_dto import OperateLogPageReqDTO
from module_system.api.logger.dto.operate_log_resp_dto import OperateLogRespDTO
from module_system.api.logger.operate_log_api import OperateLogApi
from module_system.service.logger.operate_log_service import OperateLogService


@service(interface=OperateLogApi)
class OperateLogApiImpl(OperateLogApi):
    """操作日志 API 实现类"""

    operate_log_service: OperateLogService = Inject()

    @override
    async def create_operate_log(self, req_dto: OperateLogCreateReqDTO) -> None:
        await self.operate_log_service.create_operate_log(req_dto)

    @override
    async def get_operate_log_page(
        self, page_req_dto: OperateLogPageReqDTO
    ) -> PageResult[OperateLogRespDTO]:
        operate_log_page = await self.operate_log_service.get_operate_log_page_dto(page_req_dto)
        return operate_log_page.convert(lambda item: OperateLogRespDTO.model_validate(item))
