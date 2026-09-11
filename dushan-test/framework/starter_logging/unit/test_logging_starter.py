import asyncio
import threading
from pathlib import Path

import pytest
from config_factory import ConfigFactory
from loguru import logger

from framework.starter_logging.config.log_settings import LogSettings
from framework.starter_logging.core.logger_configurator import LoggerConfigurator
from framework.starter_logging.starter import logging_starter as logging_starter_module
from framework.starter_logging.starter.logging_starter import LoggingStarter

pytestmark = pytest.mark.unit


async def test_shutdown_awaits_loguru_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """关闭流程等待 Loguru 的异步完成阶段。"""
    completed = False

    async def complete() -> None:
        """记录完成阶段是否被等待。"""
        nonlocal completed
        completed = True

    monkeypatch.setattr(logger, "complete", complete)

    await LoggingStarter(LoggerConfigurator(tmp_path)).shutdown()

    assert completed is True


async def test_shutdown_flushes_enqueued_file_sink(tmp_path: Path) -> None:
    """关闭时先排空受管文件队列，移除后不再写入新日志。"""
    log_file = tmp_path / "queued.log"
    configurator = LoggerConfigurator(base_dir=tmp_path)
    configurator._sink_ids.add(logger.add(log_file, enqueue=True, format="{message}"))
    try:
        logger.info("queued event")
        await LoggingStarter(configurator=configurator).shutdown()
        drained_text = log_file.read_text(encoding="utf-8")
        logger.info("late event")
        final_text = log_file.read_text(encoding="utf-8")
    finally:
        configurator.remove_owned_handlers()

    assert "queued event" in drained_text
    assert "late event" not in final_text
    assert final_text == drained_text


async def test_shutdown_awaits_coroutine_sink_before_removal(tmp_path) -> None:
    """异步日志输出完成后才移除本实例的输出处理器。"""
    sink_completed = False
    configurator = LoggerConfigurator(tmp_path)

    async def coroutine_sink(_message) -> None:
        """跨过一次事件循环后记录输出完成。"""
        nonlocal sink_completed
        await asyncio.sleep(0)
        sink_completed = True

    configurator._sink_ids.add(logger.add(coroutine_sink))
    try:
        logger.info("coroutine event")
        await LoggingStarter(configurator=configurator).shutdown()
    finally:
        configurator.remove_owned_handlers()

    assert sink_completed is True


async def test_shutdown_times_out_when_sync_queue_barrier_blocks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """同步队列阻塞也受关闭时限约束，超时后受管文件拒收新日志。"""
    barrier_started = threading.Event()
    barrier_release = threading.Event()
    terminal_remove_finished = threading.Event()
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(tmp_path),
        enable_file_overall=True,
        console_level="NONE",
        file_active_types={"info"},
        enqueue=False,
        compression=None,
    )
    configurator = LoggerConfigurator(base_dir=tmp_path)
    configurator.configure_logging(settings, app_env="test")
    original_remove = configurator.remove_owned_handlers

    class CompletedAwaitable:
        def __await__(self):
            """提供不再阻塞的异步完成结果。"""
            if False:
                yield None

    def blocked_complete() -> CompletedAwaitable:
        """模拟 Loguru 完成阶段的同步队列屏障。"""
        barrier_started.set()
        barrier_release.wait()
        return CompletedAwaitable()

    def observed_remove() -> None:
        """记录本实例的处理器何时移除完毕。"""
        try:
            original_remove()
        finally:
            terminal_remove_finished.set()

    monkeypatch.setattr(logger, "complete", blocked_complete)
    monkeypatch.setattr(configurator, "remove_owned_handlers", observed_remove)
    monkeypatch.setattr(LoggingStarter, "SHUTDOWN_TIMEOUT_SECONDS", 0.01)
    try:
        with pytest.raises(TimeoutError):
            await LoggingStarter(configurator=configurator).shutdown()
        logger.info("late event")
    finally:
        barrier_release.set()
        assert await asyncio.to_thread(terminal_remove_finished.wait, 1.0)
        original_remove()

    assert barrier_started.is_set()
    log_file = next(tmp_path.glob("*_info.log"))
    assert "late event" not in log_file.read_text(encoding="utf-8")


async def test_shutdown_timeout_includes_blocking_handler_removal(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """输出处理器停止时同步阻塞也不能越过关闭硬时限。"""
    stop_started = threading.Event()
    stop_release = threading.Event()
    stop_finished = threading.Event()
    configurator = LoggerConfigurator(tmp_path)

    class BlockingStopSink:
        def write(self, _message) -> None:
            """接受日志以便验证停止阶段。"""
            return

        def stop(self) -> None:
            """阻塞处理器停止，直到测试释放屏障。"""
            stop_started.set()
            stop_release.wait()
            stop_finished.set()

    configurator._sink_ids.add(logger.add(BlockingStopSink()))
    monkeypatch.setattr(LoggingStarter, "SHUTDOWN_TIMEOUT_SECONDS", 0.01)
    try:
        with pytest.raises(TimeoutError):
            await LoggingStarter(configurator=configurator).shutdown()
    finally:
        stop_release.set()
        assert await asyncio.to_thread(stop_finished.wait, 1.0)
        configurator.remove_owned_handlers()

    assert stop_started.is_set()


async def test_shutdown_reports_remove_failure_arriving_after_timeout(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """关闭已超时后到达的移除故障仍会被观察并输出脱敏原因。"""
    remove_started = threading.Event()
    remove_release = threading.Event()
    remove_finished = threading.Event()
    report_finished = threading.Event()
    configurator = LoggerConfigurator(tmp_path)
    original_report = logging_starter_module.TerminalErrorReporter.report

    class CompletedAwaitable:
        def __await__(self):
            """提供不再阻塞的异步完成结果。"""
            if False:
                yield None

    def delayed_failing_remove() -> None:
        """模拟超时后才结束的处理器移除失败。"""
        remove_started.set()
        remove_release.wait()
        try:
            raise OSError("password=late-remove-secret")
        finally:
            remove_finished.set()

    def observed_report(*args, **kwargs) -> None:
        """等待终态报告真实完成，避免线程结束与事件循环回调之间的竞争。"""
        try:
            original_report(*args, **kwargs)
        finally:
            report_finished.set()

    monkeypatch.setattr(logger, "complete", CompletedAwaitable)
    monkeypatch.setattr(configurator, "remove_owned_handlers", delayed_failing_remove)
    monkeypatch.setattr(logging_starter_module.TerminalErrorReporter, "report", observed_report)
    monkeypatch.setattr(LoggingStarter, "SHUTDOWN_TIMEOUT_SECONDS", 0.01)
    try:
        with pytest.raises(TimeoutError):
            await LoggingStarter(configurator=configurator).shutdown()
    finally:
        remove_release.set()
        assert await asyncio.to_thread(remove_finished.wait, 1.0)

    assert remove_started.is_set()
    assert await asyncio.to_thread(report_finished.wait, 1.0)
    terminal_output = capsys.readouterr().err
    assert "Loguru 后台终态失败" in terminal_output
    assert "late-remove-secret" not in terminal_output
    assert "password=***" in terminal_output


def test_initialize_preserves_primary_error_when_failure_reporting_breaks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """初始化报错时，即使错误报告也失败，仍保留最初的异常对象。"""
    primary_error = RuntimeError("file sink failed")

    class FailingConfigurator:
        def configure_logging(self, _log_settings, app_env: str) -> None:
            """模拟日志输出配置失败。"""
            assert app_env == "test"
            raise primary_error

    def broken_reporter(*_args, **_kwargs) -> None:
        """模拟终端错误报告也不可用。"""
        raise OSError("stderr closed")

    monkeypatch.setattr(logging_starter_module.TerminalErrorReporter, "report", broken_reporter)

    with pytest.raises(RuntimeError, match="file sink failed") as exc_info:
        LoggingStarter(configurator=FailingConfigurator()).initialize(
            app_env="test", log_settings=ConfigFactory.build(LogSettings, "log")
        )

    assert exc_info.value is primary_error
    assert "日志初始化失败报告未能输出：OSError" in primary_error.__notes__
