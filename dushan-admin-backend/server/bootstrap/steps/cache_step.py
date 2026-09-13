from contextlib import asynccontextmanager

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.model.cache_key_container import CacheKeyContainer
from framework.starter_cache.starter.cache_starter import CacheStarter
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
        primary = None
        try:
            await starter.open(containers)
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
