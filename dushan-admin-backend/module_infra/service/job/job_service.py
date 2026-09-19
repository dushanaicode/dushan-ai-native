from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_infra.controller.admin.job.vo.job.job_page_req_vo import JobPageReqVO
from module_infra.controller.admin.job.vo.job.job_save_req_vo import JobSaveReqVO
from module_infra.dal.dataobject.job.job_do import JobDO


@runtime_checkable
class JobService(Protocol):
    """定时任务服务接口"""

    async def create_job(self, create_req_vo: JobSaveReqVO) -> int:
        """创建定时任务"""
        ...

    async def update_job(self, update_req_vo: JobSaveReqVO) -> None:
        """更新定时任务"""
        ...

    async def update_job_status(self, job_id: int, status: int) -> None:
        """更新定时任务的状态"""
        ...

    async def trigger_job(self, job_id: int) -> None:
        """立即触发一次定时任务执行"""
        ...

    async def trigger_job_by_handler(self, handler_name: str, handler_param: str) -> None:
        """通过处理器名称和参数直接触发任务执行"""
        ...

    async def delete_job(self, id: int) -> None:
        """删除定时任务"""
        ...

    async def delete_job_batch(self, ids: list[int]) -> int:
        """批量删除定时任务"""
        ...

    async def sync_job(self) -> None:
        """同步数据库中的所有Job定义到调度器"""
        ...

    async def get_job(self, job_id: int) -> JobDO | None:
        """根据ID获取定时任务信息"""
        ...

    async def get_job_page(self, page_req_vo: JobPageReqVO) -> PageResult[JobDO]:
        """分页查询定时任务"""
        ...
