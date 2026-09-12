import asyncio
import threading
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionOwner:
    """区分实际执行线程与任务，避免继承的 ContextVar 被当成同一调用栈。"""

    thread_id: int
    task: asyncio.Task | None

    @classmethod
    def current(cls) -> "ExecutionOwner":
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        return cls(threading.get_ident(), task)
