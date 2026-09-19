from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_infra.controller.admin.logger.vo.apierrorlog.apierrorlog_api_error_log_page_req_vo import (
    ApiErrorLogPageReqVO,
)
from module_infra.dal.dataobject.logger.api_error_log_do import ApiErrorLogDO
from module_infra.spi.logger.dto.api_error_log_create_req_dto import ApiErrorLogCreateReqDTO


@runtime_checkable
class ApiErrorLogService(Protocol):
    """API 错误日志服务接口"""

    async def create_api_error_log(self, create_req_dto: ApiErrorLogCreateReqDTO) -> None:
        """创建API错误日志"""
        ...

    async def get_api_error_log_page(
        self, page_req_vo: ApiErrorLogPageReqVO
    ) -> PageResult[ApiErrorLogDO]:
        """获取API错误日志分页"""
        ...

    async def update_api_error_log_process(
        self, log_id: int, process_status: int, process_user_id: int | None
    ) -> None:
        """更新API错误日志处理状态"""
        ...

    async def clean_error_log(self, exceed_day: int, delete_limit: int) -> int:
        """清理指定天数之前的错误日志"""
        ...
