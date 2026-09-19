from contextlib import asynccontextmanager

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.starter.ip_starter import IpStarter
from server.bootstrap.context import AppBootstrapContext


class IpStep:
    """在应用就绪前加载地区和 IP 资源，业务排空后释放本应用的资源。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        if IpSettings not in definitions.configuration.model_classes:
            ctx.logger.info("【IpStarter 】配置模型未装配，跳过启动")
            yield
            return
        settings = definitions.configuration.get_config(IpSettings)
        if not settings.enabled:
            ctx.logger.info("【IpStarter 】地区与 IP 查询未启用")
            yield
            return
        if definitions.application_context is None:
            raise ValueError("启用 IP 组件要求先启用 DI")
        starter = definitions.application_context.container.get(IpStarter)
        primary = None
        try:
            await starter.open()
            ctx.app.state.ip = starter
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.ip = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "应用 IP 资源清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "IP 启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
