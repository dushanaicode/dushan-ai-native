from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_captcha.core.captcha_service import CaptchaService
from server.bootstrap.context import AppBootstrapContext


class CaptchaStep:
    """缓存就绪后打开验证码，应用排空后先关闭验证码再释放缓存。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        if CaptchaSettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(CaptchaSettings)
        if not settings.enabled:
            yield
            return
        if definitions.application_context is None:
            raise ValueError("启用验证码要求先启用 DI")
        service = definitions.application_context.container.get(CaptchaService)
        primary = None
        try:
            service.open()
            ctx.app.state.captcha = service
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.captcha = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                service.close, "验证码资源清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "验证码启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
