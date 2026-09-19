import asyncio
import sys
from collections.abc import Awaitable, Callable, Coroutine
from contextvars import Context
from typing import Any, TypeVar

from anyio import CancelScope

T = TypeVar("T")


class AsyncioUtils:
    """组织异步并发、受保护清理和由调用方持有的任务。

    并发入口接收协程工厂，确保任务不会在限流前启动；失败时取消并等待同组任务。
    应用后台任务由 ApplicationContext.tasks 登记和排空，本工具不另建任务管理器。
    context=None 继承当前上下文，传入显式 Context 可隔离执行资源，不使用全局清理注册表。
    """

    @classmethod
    async def gather_with_concurrency(
        cls, limit: int, *actions: Callable[[], Awaitable[T]]
    ) -> list[T]:
        """限制正在执行的工厂数量，并按输入顺序返回结果。"""
        if type(limit) is not int or limit <= 0:
            raise ValueError("并发上限必须是正整数")
        semaphore = asyncio.Semaphore(limit)
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(cls._run_limited(semaphore, action)) for action in actions]
        return [task.result() for task in tasks]

    @staticmethod
    async def _run_limited(semaphore: asyncio.Semaphore, action: Callable[[], Awaitable[T]]) -> T:
        """获得并发额度后才创建并执行协程。"""
        async with semaphore:
            return await action()

    @staticmethod
    async def run_cancellation_shielded(
        awaitable: Awaitable[T], *, propagate_cancellation: bool = True
    ) -> T:
        """等待清理终态再传播调用方取消；被保护操作应自行设置明确超时。"""
        active = sys.exception()
        cancellation = active if isinstance(active, asyncio.CancelledError) else None
        with CancelScope(shield=True):
            protected = asyncio.ensure_future(awaitable)
            # 独立完成信号只成功，不会混淆调用方取消与清理任务自身取消。
            completion = asyncio.get_running_loop().create_future()
            protected.add_done_callback(lambda _task: completion.set_result(None))
            while not completion.done():
                try:
                    await asyncio.shield(completion)
                except asyncio.CancelledError as exc:
                    if cancellation is None:
                        cancellation = exc
            try:
                result = protected.result()
            except BaseException as exc:
                if cancellation is not None and propagate_cancellation:
                    cancellation.add_note(f"受保护操作同时失败：{type(exc).__name__}")
                    if exc is cancellation:
                        raise cancellation from None
                    raise cancellation from exc
                raise
            if cancellation is not None and propagate_cancellation:
                raise cancellation
            return result

    @staticmethod
    def create_task(
        coro: Coroutine[Any, Any, T], *, name: str | None = None, context: Context | None = None
    ) -> asyncio.Task[T]:
        """创建由调用方持有并等待的任务，采用 Python 原生上下文传递契约。"""
        return asyncio.create_task(coro, name=name, context=context)
