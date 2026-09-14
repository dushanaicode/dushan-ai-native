from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_protection.config.protection_settings import ProtectionSettings
from framework.starter_protection.core.protection_service import ProtectionService
from server.bootstrap.context import AppBootstrapContext


class ProtectionStep:
    """Cache 打开后启动保护，业务排空后先关闭保护再关闭 Cache。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        if ProtectionSettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(ProtectionSettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise ValueError("启用保护要求先启用 DI")
            yield
            return
        service = application.container.get(ProtectionService)
        observer = None
        monitor = getattr(ctx.app.state, "monitor", None)
        if settings.tracing_enabled and monitor is not None and monitor.settings.enabled:
            from framework.starter_protection.integration.monitor_protection_observer import (
                MonitorProtectionObserver,
            )

            observer = MonitorProtectionObserver(monitor)
        primary = None
        try:
            await service.open(observer=observer)
            ctx.app.state.protection = service
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.protection = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                service.close, "应用保护资源清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "保护启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
