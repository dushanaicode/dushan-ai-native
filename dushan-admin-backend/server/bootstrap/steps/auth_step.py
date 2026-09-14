from contextlib import asynccontextmanager

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_auth.core.auth_service import AuthService
from server.bootstrap.context import AppBootstrapContext


class AuthStep:
    """缓存就绪后打开授权，应用业务排空后先关闭授权资源再释放缓存。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        ctx.app.state.auth = None
        definitions = ctx.definitions
        if AuthSettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(AuthSettings)
        if not settings.enabled:
            yield
            return
        if definitions.application_context is None:
            raise ValueError("启用第三方授权要求先启用 DI")
        service = definitions.application_context.container.get(AuthService)
        primary = None
        try:
            await service.open(
                components=definitions.scan_result.get_components(
                    component_type=ComponentTypeEnum.COMPONENT
                )
            )
            ctx.app.state.auth = service
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.auth = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                service.close, "第三方授权资源清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "第三方授权启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
