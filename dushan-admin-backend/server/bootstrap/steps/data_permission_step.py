from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_data_permission.config.data_permission_settings import DataPermissionSettings
from framework.starter_data_permission.starter.data_permission_starter import DataPermissionStarter
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_tenant.core.tenant_model_discovery import TenantModelDiscovery


class DataPermissionStep:
    """先检查应用依赖，再交给 Starter 绑定数据访问策略。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        configuration = definitions.configuration
        if DataPermissionSettings not in configuration.model_classes:
            ctx.logger.info("【DataPermissionStarter 】配置模型未装配，跳过启动")
            yield
            return
        settings = configuration.get_config(DataPermissionSettings)
        models = TenantModelDiscovery.collect(
            tuple(module.definition.package for module in definitions.modules),
            definitions.scan_result.get_components(),
        )
        if not settings.enabled:
            if any("__data_permission__" in vars(component) for component in models):
                raise ValueError("声明数据访问策略的模型要求启用 Data Permission")
            ctx.logger.info("【DataPermissionStarter 】数据权限未启用")
            yield
            return
        application = definitions.application_context
        if (
            application is None
            or ctx.app.state.database is None
            or not configuration.get_config(SecuritySettings).enabled
            or settings.cache_enabled
            and ctx.app.state.cache is None
        ):
            raise ValueError("数据权限要求 DI、Database、Security 及已配置的缓存资源就绪")
        starter = application.container.get(DataPermissionStarter)
        primary = None
        try:
            starter.open(models, ctx.app.state.database)
            yield
        except BaseException as error:
            primary = error
        finally:
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "数据权限执行排空"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "数据权限关闭失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
