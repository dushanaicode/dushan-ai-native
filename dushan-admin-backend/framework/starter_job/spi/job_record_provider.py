from typing import Protocol

from framework.starter_job.model.job_record import JobRecord


class JobRecordProvider(Protocol):
    """执行观测，写入失败不能覆写业务结果；由业务持久化与清理。"""

    async def record(self, record: JobRecord) -> None: ...
