from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.starter.database_starter import DatabaseStarter
from server.bootstrap.context import AppBootstrapContext


class DatabaseStep:
    """定义和 DI 就绪后启动数据库，全部资源就绪后才开放应用业务入口。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        if DatabaseSettings not in definitions.configuration.model_classes:
            ctx.logger.info("【DatabaseStarter 】配置模型未装配，跳过启动")
            yield
            return
        settings = definitions.configuration.get_config(DatabaseSettings)
        if not settings.enabled:
            ctx.logger.info("【DatabaseStarter 】数据库未启用")
            yield
            return
        if definitions.application_context is None:
            raise ValueError("启用数据库要求先启用 DI")
        starter = definitions.application_context.container.get(DatabaseStarter)
        primary = None
        try:
            await starter.open()
            ctx.app.state.database = starter.database
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.database = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "应用数据库资源清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "数据库启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
            ctx.logger.info("【DatabaseStarter 】数据库资源已关闭")
