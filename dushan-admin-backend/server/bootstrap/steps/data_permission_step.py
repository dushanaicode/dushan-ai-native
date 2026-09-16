from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_data_permission.config.data_permission_settings import DataPermissionSettings
from framework.starter_data_permission.core.data_permission_policy import DataPermissionPolicy
from framework.starter_data_permission.core.data_permission_registry import DataPermissionRegistry
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_data_permission.spi.data_exemption_provider import DataExemptionProvider
from framework.starter_security.config.security_settings import SecuritySettings
from server.bootstrap.context import AppBootstrapContext


class DataPermissionStep:
    """使用应用定义快照装配；不创建全局 Session 监听或业务权限样例。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        configuration = definitions.configuration
        if DataPermissionSettings not in configuration.model_classes:
            yield
            return
        settings = configuration.get_config(DataPermissionSettings)
        models = [
            component
            for component in definitions.scan_result.get_components()
            if "__table__" in vars(component) or "__data_permission__" in vars(component)
        ]
        if not settings.enabled:
            if any("__data_permission__" in vars(component) for component in models):
                raise ValueError("声明数据访问策略的模型要求启用 Data Permission")
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
        registry = DataPermissionRegistry(models)
        service = application.container.get(DataPermissionService)
        service.exemptions = application.container.get_optional(DataExemptionProvider)
        policy = DataPermissionPolicy(registry, service)
        primary = None
        with ctx.app.state.database.use_session_policy(policy):
            try:
                yield
            except BaseException as error:
                primary = error
            finally:
                error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                    service.close, "数据权限执行排空"
                )
                CleanupUtils.raise_collected_cleanup_errors(
                    "数据权限关闭失败",
                    [] if error is None else [error],
                    primary_error=primary,
                    caller_cancellation=cancellation,
                )
