from contextlib import asynccontextmanager

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.model.cache_key_container import CacheKeyContainer
from framework.starter_cache.starter.cache_starter import CacheStarter
from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_captcha.definitions.captcha_cache_keys import CaptchaCacheKeys
from framework.starter_protection.config.protection_settings import ProtectionSettings
from framework.starter_security.config.security_settings import SecuritySettings
from server.bootstrap.context import AppBootstrapContext


class CacheStep:
    """定义和 DI 就绪后建立缓存连接，并在数据库之后才释放。

    这一步排在数据库之前进入，因此关闭时在数据库之后退出：事务提交后的缓存失效
    在数据库收尾期间仍然有可用连接，不会因为缓存先关而留下没执行的失效。
    """

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        if CacheSettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(CacheSettings)
        if not settings.enabled:
            yield
            return
        if definitions.application_context is None:
            raise ValueError("启用缓存要求先启用 DI")
        starter = definitions.application_context.container.get(CacheStarter)
        containers = tuple(
            component
            for component in definitions.scan_result.get_components(
                component_type=ComponentTypeEnum.COMPONENT
            )
            if issubclass(component, CacheKeyContainer)
        )
        resource_keys = ()
        if SecuritySettings in definitions.configuration.model_classes:
            security = definitions.configuration.get_config(SecuritySettings)
            if security.enabled and security.permission_cache_enabled:
                resource_keys += (security.cache_key(),)
        if AuthSettings in definitions.configuration.model_classes:
            auth = definitions.configuration.get_config(AuthSettings)
            if auth.enabled:
                resource_keys += auth.cache_keys()
        if CaptchaSettings in definitions.configuration.model_classes:
            captcha = definitions.configuration.get_config(CaptchaSettings)
            if captcha.enabled:
                resource_keys += (CaptchaCacheKeys.state(captcha.client_name),)
        if ProtectionSettings in definitions.configuration.model_classes:
            protection = definitions.configuration.get_config(ProtectionSettings)
            if protection.enabled:
                resource_keys += (protection.cache_key(),)
        primary = None
        try:
            await starter.open(containers, resource_keys=resource_keys)
            ctx.app.state.cache = starter.cache_manager
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.cache = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "应用缓存资源清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "缓存启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
