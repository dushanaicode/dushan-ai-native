from contextlib import asynccontextmanager

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_protection.config.protection_settings import ProtectionSettings
from framework.starter_protection.starter.protection_starter import ProtectionStarter
from server.bootstrap.context import AppBootstrapContext


class ProtectionStep:
    """Cache 打开后启动保护，业务排空后先关闭保护再关闭 Cache。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        if ProtectionSettings not in definitions.configuration.model_classes:
            ctx.logger.info("【ProtectionStarter 】配置模型未装配，跳过启动")
            yield
            return
        settings = definitions.configuration.get_config(ProtectionSettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise ValueError("启用保护要求先启用 DI")
            ctx.logger.info("【ProtectionStarter 】保护能力未启用")
            yield
            return
        starter = application.container.get(ProtectionStarter)
        monitor = getattr(ctx.app.state, "monitor", None)
        primary = None
        try:
            await starter.open(monitor=monitor)
            ctx.app.state.protection = starter.service
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.protection = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "应用保护资源清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "保护启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
