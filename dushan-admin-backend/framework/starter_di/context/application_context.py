import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from threading import RLock
from typing import ClassVar, TypeVar

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
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


class ApplicationContext:
    """管理一个应用的容器、执行准入及关闭，不保存进程唯一应用。

    startup 完成 DI 初始化，mark_ready 在其他资源就绪后开放业务。
    普通函数通过 execution 或 tasks 进入所属应用，再使用 get_bean。
    关闭先排空完整业务执行，再释放容器；不会以超时为由抢先销毁依赖。
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
        self._errors: list[BaseException] = []
        container.attach_application(self, {ApplicationContext: self, DiTaskRunner: self.tasks})

    @property
    def state(self) -> ApplicationStateEnum:
        with self._lock:
            return self._state

    @classmethod
    def current(cls) -> "ApplicationContext":
        binding = cls._current.get()
        if binding is None:
            raise DiException(error_code=DiErrorCodes.CONTEXT_MISSING)
        if not binding.active:
            raise DiException(error_code=DiErrorCodes.CONTEXT_EXPIRED)
        return binding.application

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
        allowed = {
            ExecutionPhaseEnum.BUSINESS: {
                ApplicationStateEnum.READY,
                ApplicationStateEnum.DRAINING,
            },
            ExecutionPhaseEnum.INITIALIZE: {ApplicationStateEnum.STARTING},
            ExecutionPhaseEnum.CLEANUP: {
                ApplicationStateEnum.STARTING,
                ApplicationStateEnum.DRAINING,
                ApplicationStateEnum.STOPPING,
            },
        }
        if self.state not in allowed[binding.phase]:
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
        self._reject_reentrant_close()
        self.require_owner_loop()
        with self._lock:
            if self._state in {ApplicationStateEnum.STOPPING, ApplicationStateEnum.CLOSED}:
                return
            if self._drain_task is None:
                starting = self._state is ApplicationStateEnum.STARTING
                self._state = ApplicationStateEnum.DRAINING
                if starting:
                    self.tasks.cancel_pending()
                self._drain_task = asyncio.create_task(self._drain(), name="DI execution drain")
        await AsyncioUtils.run_cancellation_shielded(self._drain_task)

    async def _drain(self) -> None:
        try:
            async with asyncio.timeout(self.settings.drain_timeout_seconds):
                await self._wait_for_idle()
        except TimeoutError as error:
            self._errors.append(DiException(error_code=DiErrorCodes.DRAIN_TIMEOUT, cause=error))
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

    def record_task_error(self, error: BaseException) -> None:
        self._errors.append(DiException(error_code=DiErrorCodes.TASK_FAILED, cause=error))

    async def shutdown(self) -> None:
        self._reject_reentrant_close()
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        self.require_owner_loop()
        if self._shutdown_task is None:
            self._shutdown_task = asyncio.create_task(self._close(), name="DI application shutdown")
        await AsyncioUtils.run_cancellation_shielded(self._shutdown_task)

    async def _close(self) -> None:
        await self.drain()
        with self._lock:
            self._state = ApplicationStateEnum.STOPPING
        try:
            await self.container.shutdown()
        except BaseException as error:
            self._errors.append(error)
        finally:
            with self._lock:
                self._state = ApplicationStateEnum.CLOSED
        if self._errors:
            raise BaseExceptionGroup("应用 DI 关闭发生错误", self._errors)

    def get_statistics(self) -> dict[str, object]:
        with self._lock:
            return {
                "state": self._state.value,
                "executions": len(self._executions),
                "tasks": self.tasks.active_count,
                "errors": len(self._errors),
                "container": self.container.get_statistics(),
            }
