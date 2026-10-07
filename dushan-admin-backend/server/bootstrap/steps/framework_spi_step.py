from contextlib import asynccontextmanager, nullcontext

from framework.starter_config.config.config_settings import ConfigSettings
from framework.starter_config.spi.config_source_provider import ConfigSourceProvider
from framework.starter_database.spi.data_source_config_provider import DataSourceConfigProvider
from framework.starter_database.starter.database_starter import DatabaseStarter
from framework.starter_di.context.di_task_runner import DiTaskRunner
from framework.starter_web.exception.error_log_recorder import ErrorLogRecorder
from framework.starter_web.spi.access_log_provider import AccessLogProvider
from framework.starter_web.spi.error_log_provider import ErrorLogProvider
from server.bootstrap.app_bootstrap_context import AppBootstrapContext


class FrameworkSpiStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        """接入当前容器绑定的框架扩展，退出时恢复日志接收方。"""
        application = ctx.definitions.application_context
        if application is None:
            ctx.logger.info("【FrameworkSpiStep】未启用 DI，跳过框架扩展接入")
            yield
            return

        container = application.container
        database = ctx.app.state.database
        with database.scope() if database is not None else nullcontext():
            if database is not None and database.settings.dynamic_enabled:
                data_source = container.get_optional(DataSourceConfigProvider)
                if data_source is not None:
                    await container.get(DatabaseStarter).attach_source_loader(data_source)
            if container.get(ConfigSettings).reload_enabled:
                config_source = container.get_optional(ConfigSourceProvider)
                if config_source is not None:
                    await config_source.refresh()

        error_provider = container.get_optional(ErrorLogProvider)
        access_provider = container.get_optional(AccessLogProvider)
        tasks = container.get(DiTaskRunner) if access_provider is not None else None
        previous_recorder = ctx.exception_handler.error_recorder
        previous_provider = ctx.app.state.access_log_provider
        previous_tasks = ctx.app.state.access_log_tasks
        try:
            if error_provider is not None:
                ctx.exception_handler.error_recorder = ErrorLogRecorder(error_provider.write)
            ctx.app.state.access_log_provider = access_provider
            ctx.app.state.access_log_tasks = tasks
            ctx.logger.info("【FrameworkSpiStep】框架扩展已接入")
            yield
        finally:
            if error_provider is not None:
                ctx.exception_handler.error_recorder = previous_recorder
            ctx.app.state.access_log_provider = previous_provider
            ctx.app.state.access_log_tasks = previous_tasks
