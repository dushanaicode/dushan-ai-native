from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_tenant.config.tenant_settings import TenantSettings
from framework.starter_tenant.core.tenant_model_discovery import TenantModelDiscovery
from framework.starter_tenant.core.tenant_model_registry import TenantModelRegistry
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.starter.tenant_starter import TenantStarter


class TenantStep:
    """将租户 Starter 的资源接入应用生命周期。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if TenantSettings not in definitions.configuration.model_classes:
            ctx.logger.info("【TenantStarter 】配置模型未装配，跳过启动")
            yield
            return
        models = TenantModelDiscovery.collect(
            tuple(module.definition.package for module in definitions.modules),
            definitions.scan_result.get_components(),
        )
        application = definitions.application_context
        if application is None:
            TenantModelRegistry(models)
            if models:
                raise TenantException("configuration")
            ctx.logger.info("【TenantStarter 】未启用 DI，运行时未装配")
            yield
            return
        starter = application.container.get(TenantStarter)
        primary = None
        try:
            starter.open(models, ctx.app.state.database)
            ctx.app.state.tenant = starter.service
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.tenant = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "租户执行排空"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "租户启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
