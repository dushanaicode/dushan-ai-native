from contextlib import asynccontextmanager

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.starter.security_starter import SecurityStarter


class SecurityStep:
    """在数据库/缓存就绪后装配安全，在依赖释放前排空安全操作。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if SecuritySettings not in definitions.configuration.model_classes:
            ctx.logger.info("【SecurityStarter 】配置模型未装配，跳过启动")
            yield
            return
        settings = definitions.configuration.get_config(SecuritySettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise ValueError("启用 Security 要求先启用 DI")
            ctx.logger.info("【SecurityStarter 】本站安全未启用")
            yield
            return
        starter = application.container.get(SecurityStarter)
        primary = None
        try:
            await starter.open(
                routes=ctx.app.state.web_routes,
                database=ctx.app.state.database,
                tenant=ctx.app.state.tenant,
                expression_utils=ctx.expression_utils,
            )
            ctx.app.state.security = starter.service
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.security = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "Security 资源排空"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "Security 启停失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
