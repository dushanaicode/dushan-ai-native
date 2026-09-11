from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from framework.common.diagnostics.terminal_error_reporter import TerminalErrorReporter
from framework.common.security.sanitizer import Sanitizer
from framework.starter_logging.core.logger_configurator import LoggerConfigurator
from framework.starter_logging.starter.logging_starter import LoggingStarter
from server.bootstrap.context import AppBootstrapContext


@asynccontextmanager
async def configure_logging(ctx: AppBootstrapContext) -> AsyncIterator[None]:
    """初始化当前应用的 Loguru 输出，退出时排空队列并清理自身 sink。

    日志清理失败作为原错误的附注保留，不能覆盖正在传播的启动错误或取消信号。
    """
    starter = LoggingStarter(LoggerConfigurator(ctx.base_dir, owner_id=ctx.logging_owner))
    ctx.logging_starter = starter
    original_error: BaseException | None = None
    try:
        starter.initialize(
            app_env=ctx.settings.env.value,
            log_settings=ctx.log_settings,
        )
        yield
    except BaseException as error:
        original_error = error
        raise
    finally:
        try:
            await starter.shutdown()
        except BaseException as cleanup_error:
            if original_error is None:
                raise
            original_error.add_note(
                f"日志清理失败：{type(cleanup_error).__name__}："
                f"{Sanitizer.sanitize_log_value(cleanup_error)}"
            )
            TerminalErrorReporter.report(
                "日志清理失败，保留原始错误", cleanup_error, original_error
            )
