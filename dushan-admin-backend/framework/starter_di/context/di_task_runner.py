import asyncio
import inspect
from collections.abc import Callable
from contextvars import Context
from typing import TYPE_CHECKING, Any

from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException

if TYPE_CHECKING:
    from framework.starter_di.context.application_context import ApplicationContext
    from framework.starter_di.context.execution_binding import ExecutionBinding


class DiTaskRunner:
    """为调度、CLI 和回调建立完整执行边界，持有并回收本应用创建的后台任务。"""

    def __init__(self, application: "ApplicationContext") -> None:
        self._application = application
        self._tasks: set[asyncio.Task] = set()

    async def run(self, callback: Callable, *args, **kwargs) -> Any:
        with self._application.execution():
            result = callback(*args, **kwargs)
            return await result if inspect.isawaitable(result) else result

    def run_sync(self, callback: Callable, *args, **kwargs) -> Any:
        """在调用线程运行同步回调；阻塞线程的终止仍由回调自身负责。"""
        with self._application.execution():
            result = callback(*args, **kwargs)
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise DiException(
                    error_code=DiErrorCodes.INVALID_DEFINITION, msg="同步任务入口不能返回 awaitable"
                )
            return result

    def create_task(
        self,
        callback: Callable,
        *args,
        name: str | None = None,
        continuation: bool = False,
        **kwargs,
    ) -> asyncio.Task:
        """预先登记任务；continuation 仅允许有效业务上下文在排空时登记必要续作。"""
        self._application.require_owner_loop()
        binding = self._application.reserve_execution(
            allow_starting=True, allow_nested=continuation
        )
        task = asyncio.create_task(
            self._run_reserved(binding, callback, args, kwargs), name=name, context=Context()
        )
        self._tasks.add(task)
        task.add_done_callback(lambda finished: self._completed(finished, binding))
        return task

    async def _run_reserved(self, binding: "ExecutionBinding", callback: Callable, args, kwargs):
        try:
            await self._application.wait_until_ready()
            with self._application.activate(binding):
                result = callback(*args, **kwargs)
                return await result if inspect.isawaitable(result) else result
        finally:
            self._application.release_execution(binding)

    def _completed(self, task: asyncio.Task, binding: "ExecutionBinding") -> None:
        self._tasks.discard(task)
        # 任务可能在首次运行前就取消，此时协程的 finally 不会执行。
        self._application.release_execution(binding)
        if not task.cancelled():
            error = task.exception()
            if error is not None:
                self._application.record_task_error(error, task)

    def cancel_pending(self) -> None:
        for task in tuple(self._tasks):
            task.cancel("应用正在关闭")

    @property
    def active_count(self) -> int:
        return len(self._tasks)
