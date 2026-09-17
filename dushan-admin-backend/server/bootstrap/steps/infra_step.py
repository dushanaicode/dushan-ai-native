from contextlib import asynccontextmanager


class InfraStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        if "infra" not in ctx.module_settings.enabled:
            yield
            return
        from framework.starter_config.config.config_settings import ConfigSettings
        from framework.starter_database.spi.data_source_config_provider import (
            DataSourceConfigProvider,
        )
        from framework.starter_database.starter.database_starter import DatabaseStarter
        from framework.starter_web.exception.error_log_recorder import ErrorLogRecorder
        from module_infra.spi.config.config_support_provider_adapter import (
            ConfigSupportProviderAdapter,
        )
        from module_infra.spi.logger.api_error_log_service_provider_adapter import (
            ApiErrorLogServiceProviderAdapter,
        )

        application = ctx.definitions.application_context
        previous = ctx.exception_handler.error_recorder
        with ctx.app.state.database.scope():
            starter = application.container.get(DatabaseStarter)
            if starter.database.settings.dynamic_enabled:
                await starter.attach_source_loader(
                    application.container.get(DataSourceConfigProvider)
                )
            if application.container.get(ConfigSettings).reload_enabled:
                await application.container.get(ConfigSupportProviderAdapter).refresh()
        ctx.exception_handler.error_recorder = ErrorLogRecorder(
            application.container.get(ApiErrorLogServiceProviderAdapter).write
        )
        try:
            ctx.logger.info("【InfraStep 】基础设施适配已接入")
            yield
        finally:
            ctx.exception_handler.error_recorder = previous
