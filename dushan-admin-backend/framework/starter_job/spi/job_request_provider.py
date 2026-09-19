from datetime import datetime
from typing import Protocol

from framework.starter_job.definitions.enums.job_state import JobState
from framework.starter_job.model.job_request import JobRequest


class JobRequestProvider(Protocol):
    """owner 的跨进程有界信箱，由业务存储实现，不能在 Web 进程执行回调。

    submit 按 request_id 去重并原子检查 pending_limit；定时请求同时推进永久调度游标。
    claim 原子领取到期请求且绑定 owner；过期在途不能自动重放未知业务结果。
    finish/retry 必须核对 owner。游标不随历史记录清理丢失；重试计数持久化。
    """

    async def submit(self, request: JobRequest, *, pending_limit: int) -> bool: ...
    async def checkpoint(self, job_id: str) -> datetime | None: ...
    async def claim(
        self, owner: str, *, exclude_jobs: frozenset[str], now: datetime
    ) -> JobRequest | None: ...
    async def finish(self, request_id: str, owner: str, state: JobState) -> None: ...
    async def retry(self, request: JobRequest, owner: str) -> None: ...
    async def notify_changed(self) -> None:
        """提交后发布合并的定义变更提示；丢失提示仍由周期收敛恢复。"""
        ...

    async def consume_changes(self) -> bool: ...
