import asyncio
from dataclasses import dataclass

from framework.starter_ip.model.ip_location import IpLocation


@dataclass(slots=True)
class InflightIpQuery:
    """一轮共享查询的任务、实际等待者与失败观察状态。"""

    task: asyncio.Task[IpLocation]
    deadline_timer: asyncio.TimerHandle
    waiters: int = 0
    error_observed: bool = False
    budget_expired: bool = False
