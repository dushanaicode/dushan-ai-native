import os
from collections.abc import Mapping, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from types import MappingProxyType

from fastapi import FastAPI

from framework.common.datetime.core.date_utils import DateUtils
from framework.common.exception.core.exception_handler import GlobalExceptionHandler
from framework.common.response.core.middleware_result import MiddlewareResult
from framework.common.utils.el.expression_utils import ExpressionUtils
from framework.starter_config.provider.bootstrap_config_provider import (
    BootstrapConfigProvider,
)
from framework.starter_di.context.di_context_middleware import DiContextMiddleware
from server.bootstrap.bootstrapper import bootstrap_app
from server.bootstrap.context import AppBootstrapContext
from server.bootstrap.step_registry import BootstrapStepSpec
from server.bootstrap.steps.banner_step import BannerStep
from server.config.application_settings import ApplicationSettings
from server.routing.business_openapi import BusinessOpenAPI
from server.routing.health_router import router as health_router

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def create_app(
    *,
    base_dir: str | Path | None = None,
    app_env: str | None = None,
    environ: Mapping[str, str] | None = None,
    steps: Sequence[BootstrapStepSpec] | None = None,
) -> FastAPI:
    """创建应用并注册异常处理器、生命周期和健康检查路由。"""
    process_env = dict(os.environ if environ is None else environ)
    config_root = (
        base_dir if base_dir is not None else process_env.get("DUSHAN_CONFIG_DIR", BACKEND_ROOT)
    )
    provider = BootstrapConfigProvider.load(config_root, app_env=app_env, environ=process_env)
    configuration = provider.get_config(ApplicationSettings)
    settings = configuration.server

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """通过启动管理器完成服务启动和退出清理。"""
        async with bootstrap_app(application.state.bootstrap, steps):
            # 先排空异步日志，避免“服务已就绪”落到最终摘要之后。
            await application.state.bootstrap.logger.complete()
            BannerStep.show_startup_info(application.state.bootstrap)
            yield

    application = FastAPI(
        title=settings.name,
        version=settings.version,
        # 调试详情统一经过安全响应构造器，避免框架直接返回裸堆栈。
        debug=False,
        root_path=settings.root_path,
        lifespan=lifespan,
        docs_url=settings.docs_url if settings.docs_enabled else None,
        redoc_url=settings.redoc_url if settings.docs_enabled else None,
        openapi_url=settings.openapi_url if settings.docs_enabled else None,
    )
    exception_handler = GlobalExceptionHandler(debug=settings.debug)
    application.state.application_context = None
    application.add_middleware(DiContextMiddleware)
    exception_handler.register(application)
    application.openapi = BusinessOpenAPI(application).build
    application.state.bootstrap = AppBootstrapContext(
        application,
        provider.base_dir,
        settings,
        config_sources=MappingProxyType(provider.get_sources(ApplicationSettings)),
        log_settings=configuration.log,
        i18n_options=configuration.i18n,
        exception_handler=exception_handler,
        page_settings=configuration.page,
        response_settings=configuration.response,
        middleware_result=MiddlewareResult(debug=settings.debug),
        date_utils=DateUtils(configuration.datetime),
        expression_utils=ExpressionUtils(configuration.expression),
        banner_settings=configuration.banner,
        module_settings=configuration.modules,
        scanner_config=configuration.scanner,
        bootstrap_config=provider,
        di_settings=configuration.di,
    )
    application.include_router(health_router)
    return application


app = create_app()
