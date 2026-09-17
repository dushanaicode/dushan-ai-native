from framework.starter_web.banner.banner_application_runner import BannerApplicationRunner
from framework.starter_web.banner.banner_runtime_info import BannerRuntimeInfo
from server.bootstrap.context import AppBootstrapContext


class BannerStep:
    """在应用成功就绪后显示最后一份摘要；字符横幅由启动器提前打印。"""

    @staticmethod
    async def show_startup_info(ctx: AppBootstrapContext) -> None:
        """从真实配置和已完成的应用定义快照构造摘要。"""
        settings = ctx.settings
        enabled = (
            tuple(module.definition.name for module in ctx.definitions.modules)
            if ctx.definitions is not None
            else ()
        )
        info = BannerRuntimeInfo(
            app_name=settings.name,
            version=settings.version,
            environment=settings.env.value,
            engine=settings.engine.value,
            host=settings.host,
            port=settings.port,
            root_path=settings.root_path,
            docs_url=settings.docs_url if settings.docs_enabled else None,
            redoc_url=settings.redoc_url if settings.docs_enabled else None,
            openapi_url=settings.openapi_url if settings.docs_enabled else None,
            enabled_modules=enabled,
            disabled_modules=tuple(
                name for name in ctx.module_settings.enabled if name not in enabled
            ),
        )
        await BannerApplicationRunner(ctx.banner_settings).print_startup_complete(info)
