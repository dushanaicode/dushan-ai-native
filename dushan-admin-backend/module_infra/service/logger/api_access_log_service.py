from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_infra.controller.admin.logger.vo.apiaccesslog.apiaccesslog_api_access_log_page_req_vo import (
    ApiAccessLogPageReqVO,
)
from module_infra.dal.dataobject.logger.api_access_log_do import ApiAccessLogDO
from module_infra.spi.logger.dto.api_access_log_create_req_dto import ApiAccessLogCreateReqDTO


@runtime_checkable
class ApiAccessLogService(Protocol):
    """API 访问日志服务接口"""

    async def create_api_access_log(self, create_req_dto: ApiAccessLogCreateReqDTO) -> None:
        """创建API访问日志"""
        ...

    async def get_api_access_log_page(
        self, page_req_vo: ApiAccessLogPageReqVO
    ) -> PageResult[ApiAccessLogDO]:
        """获取API访问日志分页"""
        ...

    async def clean_access_log(self, exceed_day: int, delete_limit: int) -> int:
        """清理指定天数之前的访问日志"""
        ...
