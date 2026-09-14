from contextlib import ExitStack, asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_monitor.config.monitor_settings import MonitorSettings
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.integration.monitor_query_observer import MonitorQueryObserver
from server.bootstrap.context import AppBootstrapContext


class MonitorStep:
    """定义装配后打开追踪，其他资源关闭后排空导出；不依赖数据库已启用。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        if MonitorSettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(MonitorSettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise ValueError("启用Monitor要求应用DI已装配")
            yield
            return
        monitor = application.container.get(MonitorService)
        previous = ctx.exception_handler.trace_reporter
        primary = None
        bindings = ExitStack()
        try:
            await monitor.open(diagnostic_logger=ctx.logger)
            if settings.enabled:
                if DatabaseSettings in definitions.configuration.model_classes:
                    database_settings = definitions.configuration.get_config(DatabaseSettings)
                    if database_settings.enabled:
                        database = application.container.get(SessionProvider)
                        monitor.database = database
                        if settings.query_enabled:
                            bindings.enter_context(
                                database.observe_queries(MonitorQueryObserver(monitor))
                            )
                ctx.exception_handler.trace_reporter = monitor
            ctx.app.state.monitor = monitor
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.monitor = None
            if ctx.exception_handler.trace_reporter is monitor:
                ctx.exception_handler.trace_reporter = previous
            bindings.close()
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                monitor.close, "追踪资源清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "追踪启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
