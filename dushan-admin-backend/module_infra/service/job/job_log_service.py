from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_infra.controller.admin.job.vo.log.log_page_req_vo import JobLogPageReqVO
from module_infra.dal.dataobject.job.job_log_do import JobLogDO


@runtime_checkable
class JobLogService(Protocol):
    """Job 日志服务接口"""

    async def get_job_log(self, log_id: int) -> JobLogDO | None:
        """获得定时任务日志"""
        ...

    async def get_job_log_page(self, page_req_vo: JobLogPageReqVO) -> PageResult[JobLogDO]:
        """获得定时任务日志分页"""
        ...

    async def clean_job_log(self, exceed_day: int, delete_limit: int) -> int:
        """清理指定天数之前的任务日志"""
        ...

    async def record(self, record): ...
