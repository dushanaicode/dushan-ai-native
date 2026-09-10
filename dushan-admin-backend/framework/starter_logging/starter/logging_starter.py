import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from threading import Thread
from typing import cast

from loguru import logger

from framework.common.diagnostics.terminal_error_reporter import TerminalErrorReporter
from framework.common.security.sanitizer import Sanitizer
from framework.starter_logging.config.log_config_builder import LogConfigBuilder
from framework.starter_logging.config.log_settings import LogSettings
from framework.starter_logging.core.logger_configurator import LoggerConfigurator


def _run_logger_action(result_future: Future[object], action: Callable[[], object]) -> None:
    """在 daemon 线程中执行一个可能同步阻塞的 Loguru 动作。"""
    try:
        result = action()
    except BaseException as error:
        result_future.set_exception(error)
    else:
        result_future.set_result(result)


def _observe_completion_future(future: asyncio.Future[object]) -> None:
    """观察超时后才到达的线程异常，避免事件循环报告未消费异常。"""
    if not future.cancelled():
        future.exception()


@dataclass(slots=True)
class _TerminalShutdownObserver:
    """记录调用方是否已停止等待后台日志清理。"""

    detached: bool = False


def _observe_terminal_task(
    future: asyncio.Future[object],
    *,
    observer: _TerminalShutdownObserver,
) -> None:
    """观察后台清理的最终结果，调用方已离开时仍报告失败。"""
    if future.cancelled():
        return
    error = future.exception()
    if error is not None and observer.detached:
        TerminalErrorReporter.report("Loguru 后台终态失败", error)


async def _run_logger_action_in_daemon(action: Callable[[], object], name: str) -> object:
    """让同步日志动作在 daemon 线程执行，取消等待不取消其最终清理。"""
    result_future: Future[object] = Future()
    Thread(
        target=_run_logger_action,
        args=(result_future, action),
        name=name,
        daemon=True,
    ).start()
    action_future = asyncio.wrap_future(result_future)
    action_future.add_done_callback(_observe_completion_future)
    return await asyncio.shield(action_future)


async def _terminate_logger(deadline: float, configurator: LoggerConfigurator) -> None:
    """在期限内排空日志，随后完成本实例输出的终态清理。"""
    terminal_error: BaseException | None = None
    try:
        async with asyncio.timeout_at(deadline):
            completion = cast(
                Awaitable[None],
                await _run_logger_action_in_daemon(logger.complete, "Loguru queue drain"),
            )
            await completion
    except BaseException as error:
        terminal_error = error

    try:
        await _run_logger_action_in_daemon(
            configurator.remove_owned_handlers, "Loguru handler removal"
        )
    except BaseException as removal_error:
        if terminal_error is None:
            raise
        terminal_error.add_note(
            "Loguru 输出移除失败：{}：{}".format(
                type(removal_error).__name__,
                Sanitizer.sanitize_log_value(removal_error),
            )
        )
    if terminal_error is not None:
        raise terminal_error


class LoggingStarter:
    """在其他资源启动前配置日志，并在它们关闭后排空队列、释放本实例输出。

    initialize(app_env="dev") 会读取配置；已有配置可用 log_settings 参数直接传入。
    同一实例初始化成功后重复调用会跳过，初始化失败后可以重试。
    无论初始化是否成功，拥有本实例的生命周期都应在 finally 中 await shutdown()。
    关闭有硬期限，超时或取消后后台仍继续移除输出；清理完成前不能重新初始化。
    """

    SHUTDOWN_TIMEOUT_SECONDS = 30.0

    def __init__(self, configurator: LoggerConfigurator | None = None):
        """保存配置器和当前实例的初始化、关闭状态。"""
        self._configurator = configurator or LoggerConfigurator()
        self._initialized = False
        self._shutdown_task: asyncio.Task[None] | None = None
        self._shutdown_deadline: float | None = None
        self._shutdown_observer: _TerminalShutdownObserver | None = None

    @property
    def initialized(self) -> bool:
        """返回当前实例是否已成功初始化。"""
        return self._initialized

    def initialize(
        self,
        *,
        app_env: str,
        base_dir: Path | str | None = None,
        log_settings: LogSettings | None = None,
    ) -> None:
        """从显式配置或配置目录初始化日志，保留失败原因以便上层回滚。"""
        if self._shutdown_task is not None and not self._shutdown_task.done():
            raise RuntimeError("日志仍在关闭，请等待输出清理完成后再初始化")
        if self._initialized:
            logger.bind(logging_owner=self._configurator.owner_id).debug("日志系统已初始化，跳过")
            return

        self._shutdown_task = None
        self._shutdown_deadline = None
        self._shutdown_observer = None
        try:
            if log_settings is None:
                base_dir_value = str(base_dir) if base_dir is not None else None
                log_settings = LogConfigBuilder.get_config(base_dir=base_dir_value, app_env=app_env)
            self._configurator.configure_logging(log_settings, app_env=app_env)
            self._initialized = True
            logger.bind(logging_owner=self._configurator.owner_id).info("日志系统初始化完成")
        except Exception as e:
            self._initialized = False
            try:
                # 配置读取可能早于安全 sink 安装，直接使用独立的脱敏终端出口。
                TerminalErrorReporter.report("LoggingStarter 日志系统初始化失败", e, note_target=e)
            except Exception as report_error:
                e.add_note(f"日志初始化失败报告未能输出：{type(report_error).__name__}")
            raise

    async def shutdown(self) -> None:
        """在硬时限内排空队列并移除自身输出，超时后仍观察后台清理结果。"""
        self._configurator.disable_managed_sinks()
        self._initialized = False
        loop = asyncio.get_running_loop()
        if self._shutdown_task is None:
            self._shutdown_deadline = loop.time() + self.SHUTDOWN_TIMEOUT_SECONDS
            self._shutdown_observer = _TerminalShutdownObserver()
            self._shutdown_task = asyncio.create_task(
                _terminate_logger(self._shutdown_deadline, self._configurator),
                name="Loguru terminal shutdown",
            )
            self._shutdown_task.add_done_callback(
                partial(_observe_terminal_task, observer=self._shutdown_observer)
            )
        terminal_task = self._shutdown_task
        observer = self._shutdown_observer
        try:
            async with asyncio.timeout_at(self._shutdown_deadline):
                await asyncio.shield(terminal_task)
        except BaseException as wait_error:
            if not terminal_task.done():
                assert observer is not None
                observer.detached = True
            elif not terminal_task.cancelled():
                terminal_error = terminal_task.exception()
                if terminal_error is not None and terminal_error is not wait_error:
                    TerminalErrorReporter.report("Loguru 后台终态失败", terminal_error)
            raise
