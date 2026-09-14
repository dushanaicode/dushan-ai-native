import asyncio
from collections import deque
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from threading import RLock
from types import MappingProxyType
from typing import ClassVar, TypeVar

from loguru import logger

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_di.context.di_task_runner import DiTaskRunner
from framework.starter_di.context.execution_binding import ExecutionBinding
from framework.starter_di.context.execution_phase_enum import ExecutionPhaseEnum
from framework.starter_di.core.di_container import DiContainer
from framework.starter_di.enums.lifecycle_phase_enum import LifecyclePhaseEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException

T = TypeVar("T")

# 各执行阶段允许解析依赖的应用状态；只读，避免每次解析重建映射。
_RESOLUTION_STATES: Mapping[ExecutionPhaseEnum, frozenset[ApplicationStateEnum]] = MappingProxyType(
    {
        ExecutionPhaseEnum.BUSINESS: frozenset(
            {ApplicationStateEnum.READY, ApplicationStateEnum.DRAINING}
        ),
        ExecutionPhaseEnum.INITIALIZE: frozenset({ApplicationStateEnum.STARTING}),
        ExecutionPhaseEnum.CLEANUP: frozenset(
            {
                ApplicationStateEnum.STARTING,
                ApplicationStateEnum.DRAINING,
                ApplicationStateEnum.STOPPING,
            }
        ),
    }
)


class ApplicationContext:
    """管理一个应用的容器、执行准入及关闭，不保存进程唯一应用。

    startup 完成 DI 初始化，mark_ready 在其他资源就绪后开放业务。
    普通函数通过 execution 或 tasks 进入所属应用，再使用 get_bean。
    关闭先排空完整业务执行，再释放容器；不会以超时为由抢先销毁依赖。
    drain/shutdown 只是对共享终态任务的等待，调用方可以取消或限时；
    取消等待不会取消、遗失或加速实际清理，框架所有者需要终态时
    用 CleanupUtils.run_cancellation_safe_cleanup 包住同一入口。
    """

    _current: ClassVar[ContextVar[ExecutionBinding | None]] = ContextVar(
        "dushan_di_execution", default=None
    )

    def __init__(self, container: DiContainer) -> None:
        self.container = container
        self.settings = container.settings
        self.tasks = DiTaskRunner(self)
        self._state = ApplicationStateEnum.NEW
        self._lock = RLock()
        self._executions: set[ExecutionBinding] = set()
        self._idle = asyncio.Event()
        self._ready = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._drain_task: asyncio.Task | None = None
        self._shutdown_task: asyncio.Task | None = None
        # 排空/销毁错误与后台任务失败分开保存，后台样本淘汰不会覆盖关闭失败。
        self._shutdown_errors: list[BaseException] = []
        self._task_errors: deque[DiException] = deque(maxlen=self.settings.task_error_limit)
        self._task_failures = 0
        container.attach_application(self, {ApplicationContext: self, DiTaskRunner: self.tasks})

    @property
    def state(self) -> ApplicationStateEnum:
        with self._lock:
            return self._state

    @classmethod
    def current(cls) -> "ApplicationContext":
        return cls.current_execution().application

    @classmethod
    def current_execution(cls) -> ExecutionBinding:
        """读取当前有效执行的身份，供上下文适配核对同一边界，不创建执行。"""
        binding = cls._current.get()
        if binding is None:
            raise DiException(error_code=DiErrorCodes.CONTEXT_MISSING)
        if not binding.active:
            raise DiException(error_code=DiErrorCodes.CONTEXT_EXPIRED)
        return binding

    async def startup(self) -> None:
        with self._lock:
            if self._state is not ApplicationStateEnum.NEW:
                raise DiException(error_code=DiErrorCodes.NOT_READY)
            self._loop = asyncio.get_running_loop()
            self._state = ApplicationStateEnum.STARTING
        try:
            with self._phase_access(LifecyclePhaseEnum.INITIALIZE):
                await self.container.startup()
        except BaseException as primary:
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                self.shutdown, "应用 DI 初始化回滚"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "应用 DI 初始化与回滚失败",
                [] if error is None else [error],
                caller_cancellation=cancellation,
                primary_error=primary,
            )

    def mark_ready(self) -> None:
        self.require_owner_loop()
        with self._lock:
            if self._state is not ApplicationStateEnum.STARTING:
                raise DiException(error_code=DiErrorCodes.NOT_READY)
            self._state = ApplicationStateEnum.READY
            self._ready.set()

    def require_owner_loop(self) -> None:
        if asyncio.get_running_loop() is not self._loop:
            raise DiException(
                error_code=DiErrorCodes.INVALID_LIFECYCLE,
                msg="应用生命周期和任务创建须在所属事件循环执行",
            )

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    def get_bean(self, bean_type: type[T]) -> T:
        if not self.settings.lookup_enabled:
            raise DiException(error_code=DiErrorCodes.LOOKUP_DISABLED)
        return self.container.get(bean_type)

    def validate_resolution(self) -> None:
        if self.current() is not self:
            raise DiException(error_code=DiErrorCodes.CONTEXT_MISMATCH)
        binding = self._current.get()
        if self.state not in _RESOLUTION_STATES[binding.phase]:
            raise DiException(error_code=DiErrorCodes.NOT_READY)

    def reserve_execution(
        self, *, allow_starting: bool = False, allow_nested: bool = False
    ) -> ExecutionBinding:
        with self._lock:
            parent = self._current.get()
            continuing = (
                allow_nested
                and parent in self._executions
                and parent.active
                and parent.phase is ExecutionPhaseEnum.BUSINESS
            )
            if self._state is ApplicationStateEnum.STARTING and allow_starting:
                self.validate_resolution()
            elif self._state is ApplicationStateEnum.DRAINING and continuing:
                pass
            elif self._state is not ApplicationStateEnum.READY:
                raise DiException(error_code=DiErrorCodes.NOT_READY)
            binding = ExecutionBinding(self, ExecutionPhaseEnum.BUSINESS)
            self._executions.add(binding)
            return binding

    def release_execution(self, binding: ExecutionBinding) -> None:
        with self._lock:
            if binding in self._executions:
                self._executions.remove(binding)
                binding.active = False
            if not self._executions:
                self._loop.call_soon_threadsafe(self._idle.set)

    @contextmanager
    def activate(self, binding: ExecutionBinding):
        token = self._current.set(binding)
        try:
            yield
        finally:
            self._current.reset(token)

    @contextmanager
    def execution(self):
        """同步和异步业务均用 with 包住完整调用，嵌套执行各自登记并恢复。"""
        binding = self.reserve_execution(allow_nested=True)
        try:
            with self.activate(binding):
                yield self
        finally:
            self.release_execution(binding)

    @contextmanager
    def _phase_access(self, phase: LifecyclePhaseEnum):
        kind = (
            ExecutionPhaseEnum.INITIALIZE
            if phase is LifecyclePhaseEnum.INITIALIZE
            else ExecutionPhaseEnum.CLEANUP
        )
        binding = ExecutionBinding(self, kind)
        try:
            with self.activate(binding):
                yield
        finally:
            binding.active = False

    def _reject_reentrant_close(self) -> None:
        binding = self._current.get()
        if binding is not None and binding.application is self and binding.active:
            raise DiException(
                error_code=DiErrorCodes.INVALID_LIFECYCLE,
                msg="活动业务或生命周期回调不能等待自身应用关闭",
            )

    async def drain(self) -> None:
        """等待业务排空；调用方取消或限时只放弃等待，排空任务继续到真实归零。"""
        self._reject_reentrant_close()
        self.require_owner_loop()
        task = self._begin_drain()
        if task is not None:
            await asyncio.shield(task)

    def _begin_drain(self) -> asyncio.Task | None:
        """进入 DRAINING 并启动唯一排空任务；已在销毁阶段时没有可等待的排空。"""
        with self._lock:
            if self._state in {ApplicationStateEnum.STOPPING, ApplicationStateEnum.CLOSED}:
                return None
            if self._drain_task is None:
                starting = self._state is ApplicationStateEnum.STARTING
                self._state = ApplicationStateEnum.DRAINING
                if starting:
                    self.tasks.cancel_pending()
                self._drain_task = asyncio.create_task(self._drain(), name="DI execution drain")
            return self._drain_task

    async def _drain(self) -> None:
        try:
            async with asyncio.timeout(self.settings.drain_timeout_seconds):
                await self._wait_for_idle()
        except TimeoutError as error:
            with self._lock:
                executions, tasks = len(self._executions), self.tasks.active_count
                self._shutdown_errors.append(
                    DiException(
                        error_code=DiErrorCodes.DRAIN_TIMEOUT,
                        msg=f"业务排空超过 {self.settings.drain_timeout_seconds} 秒："
                        f"活动执行 {executions}，受管任务 {tasks}",
                        cause=error,
                    )
                )
            logger.warning(
                "应用业务排空超过 {} 秒：活动执行 {}，受管任务 {}；已协作取消受管任务，继续等待实际结束",
                self.settings.drain_timeout_seconds,
                executions,
                tasks,
            )
            self.tasks.cancel_pending()
            # 超时不能证明线程或拒绝取消的业务已结束，资源必须继续保留。
            await self._wait_for_idle()

    async def _wait_for_idle(self) -> None:
        while True:
            with self._lock:
                if not self._executions and not self.tasks.active_count:
                    return
                self._idle.clear()
            await self._idle.wait()

    def record_task_error(self, error: BaseException, task: asyncio.Task | None = None) -> None:
        """后台任务失败立即记录 ERROR 并计入有界样本；累计次数不因样本淘汰减少。"""
        name = "<unnamed>" if task is None else task.get_name()
        with self._lock:
            self._task_failures += 1
            self._task_errors.append(
                DiException(
                    error_code=DiErrorCodes.TASK_FAILED,
                    msg=f"应用后台任务失败：{name}",
                    cause=error,
                )
            )
        logger.error(
            "应用后台任务失败：{}\n{}", name, "".join(ExceptionTraceFormatter.format(error))
        )

    async def shutdown(self) -> None:
        """等待应用关闭终态；取消或限时只放弃等待，关闭任务由本应用持有并继续完成。"""
        self._reject_reentrant_close()
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        self.require_owner_loop()
        await asyncio.shield(self._begin_shutdown())

    def _begin_shutdown(self) -> asyncio.Task:
        """启动唯一关闭任务；失败由 done callback 记录，没有等待者也不遗失。"""
        if self._shutdown_task is None:
            self._shutdown_task = asyncio.create_task(self._close(), name="DI application shutdown")
            self._shutdown_task.add_done_callback(self._shutdown_finished)
        return self._shutdown_task

    def _shutdown_finished(self, task: asyncio.Task) -> None:
        if task.cancelled():
            logger.error("应用 DI 关闭任务在完成前被事件循环取消，状态 {}", self.state.value)
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "应用 DI 关闭发生错误：\n{}", "".join(ExceptionTraceFormatter.format(error))
            )

    async def _close(self) -> None:
        drain = self._begin_drain()
        if drain is not None:
            await drain
        with self._lock:
            self._state = ApplicationStateEnum.STOPPING
        try:
            await self.container.shutdown()
        except asyncio.CancelledError:
            # 只有事件循环拆除会取消关闭任务本身；容器未确认销毁完成，不宣称 CLOSED。
            raise
        except BaseException as error:
            self._shutdown_errors.append(error)
        with self._lock:
            self._state = ApplicationStateEnum.CLOSED
        errors = self._collect_shutdown_errors()
        if errors:
            raise BaseExceptionGroup("应用 DI 关闭发生错误", errors)

    def _collect_shutdown_errors(self) -> list[BaseException]:
        """关闭报告：排空/销毁错误在前，后台失败样本其后，超出上限的部分只给摘要。"""
        with self._lock:
            errors: list[BaseException] = [*self._shutdown_errors, *self._task_errors]
            evicted = self._task_failures - len(self._task_errors)
        if evicted > 0:
            errors.append(
                DiException(
                    error_code=DiErrorCodes.TASK_FAILED,
                    msg=f"另有 {evicted} 项后台任务失败超出保留上限 "
                    f"{self.settings.task_error_limit}，详见运行日志",
                )
            )
        return errors

    def get_statistics(self) -> dict[str, object]:
        with self._lock:
            return {
                "state": self._state.value,
                "executions": len(self._executions),
                "tasks": self.tasks.active_count,
                "shutdown_errors": len(self._shutdown_errors),
                "task_failures": self._task_failures,
                "task_errors_retained": len(self._task_errors),
                "container": self.container.get_statistics(),
            }
