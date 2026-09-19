import asyncio
from collections.abc import Awaitable, Callable

from framework.common.utils.asyncio_utils import AsyncioUtils

type AsyncCleanupAction = Callable[[], Awaitable[None]]


class CleanupUtils:
    """收集异步清理错误，保留主异常与调用方取消，不丢弃资源失败的原因。"""

    @classmethod
    async def run_cancellation_safe_cleanup(
        cls, action: AsyncCleanupAction, operation: str
    ) -> tuple[BaseException | None, asyncio.CancelledError | None]:
        """在受保护任务中清理，分别返回清理错误和调用方取消。"""
        task = asyncio.create_task(cls._capture_cleanup_error(action), name=operation)
        try:
            error = await AsyncioUtils.run_cancellation_shielded(task)
        except asyncio.CancelledError as cancellation:
            return task.result(), cancellation
        return error, None

    @staticmethod
    async def _capture_cleanup_error(action: AsyncCleanupAction) -> BaseException | None:
        """将清理自身的失败转换为可聚合的结果，包括其自身取消。"""
        try:
            await action()
        except BaseException as error:
            return error
        return None

    @staticmethod
    def raise_collected_cleanup_errors(
        operation: str,
        errors: list[BaseException],
        *,
        caller_cancellation: asyncio.CancelledError | None = None,
        primary_error: BaseException | None = None,
    ) -> None:
        """优先保留主取消、调用方取消或主错误，并通过异常链保留清理错误组。"""
        terminal = (
            primary_error
            if isinstance(primary_error, asyncio.CancelledError)
            else caller_cancellation
            if caller_cancellation is not None
            else primary_error
        )
        related = [error for error in errors if error is not terminal]
        if primary_error is not None and primary_error is not terminal:
            related.insert(0, primary_error)
        if terminal is not None:
            if related:
                raise terminal from BaseExceptionGroup(operation, related)
            raise terminal
        if related:
            raise BaseExceptionGroup(operation, related)
