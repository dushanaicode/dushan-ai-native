import logging
import os
from collections.abc import Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from framework.common.dates.date_utils import DateUtils
from framework.starter_config.provider.bootstrap_config_provider import (
    BootstrapConfigProvider,
)
from framework.starter_database.context.database_middleware import DatabaseMiddleware
from framework.starter_di.context.di_context_middleware import DiContextMiddleware
from framework.starter_monitor.integration.monitor_middleware import MonitorMiddleware
from framework.starter_security.bizlog.expression.expression_utils import ExpressionUtils
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.integration.security_exception_handler import (
    SecurityExceptionHandler,
)
from framework.starter_tenant.middleware.tenant_selector_middleware import TenantSelectorMiddleware
from framework.starter_web.exception.exception_handler import GlobalExceptionHandler
from framework.starter_web.middleware.body_limit_middleware import BodyLimitMiddleware
from framework.starter_web.middleware.http_protocol_middleware import HttpProtocolMiddleware
from framework.starter_web.middleware.reported_failure_filter import ReportedFailureFilter
from framework.starter_web.middleware.request_context_middleware import RequestContextMiddleware
from framework.starter_web.middleware.response_compression_middleware import (
    ResponseCompressionMiddleware,
)
from framework.starter_web.middleware.web_exception_middleware import WebExceptionMiddleware
from framework.starter_web.response.middleware_result import MiddlewareResult
from framework.starter_web.routing.route_registrar import RouteRegistrar
from framework.starter_web.routing.router_registration import RouterRegistration
from framework.starter_web.routing.stream_response_policy import StreamResponsePolicy
from framework.starter_web.routing.web_route import WebRoute
from server.bootstrap.bootstrapper import bootstrap_app
from server.bootstrap.context import AppBootstrapContext
from server.bootstrap.step_registry import BootstrapStepSpec
from server.bootstrap.steps.banner_step import BannerStep
from server.config.application_settings import ApplicationSettings
from server.enums.server_engine_enum import ServerEngineEnum
from server.middleware.readiness_middleware import ReadinessMiddleware
from server.routing.business_openapi import BusinessOpenAPI
from server.routing.health_router import router as health_router

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def create_app(
    *,
    base_dir: str | Path | None = None,
    app_env: str | None = None,
    environ: Mapping[str, str] | None = None,
    steps: Sequence[BootstrapStepSpec] | None = None,
    routers: Sequence[RouterRegistration] = (),
    access_provider: Callable | None = None,
    engine: ServerEngineEnum | str | None = None,
) -> FastAPI:
    """创建应用并注册异常处理器、生命周期和健康检查路由。"""
    process_env = dict(os.environ if environ is None else environ)
    if engine is not None:
        process_env["SERVER_ENGINE"] = ServerEngineEnum(engine).value
    config_root = (
        base_dir if base_dir is not None else process_env.get("DUSHAN_CONFIG_DIR", BACKEND_ROOT)
    )
    provider = BootstrapConfigProvider.load(config_root, app_env=app_env, environ=process_env)
    configuration = provider.get_config(ApplicationSettings)
    settings = configuration.server
    logging_owner = uuid4().hex

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """通过启动管理器完成服务启动和退出清理。"""
        error_filter = ReportedFailureFilter(logging_owner)
        engine_loggers = [logging.getLogger(name) for name in ("uvicorn.error", "_granian")]
        filter_targets = [
            *engine_loggers,
            *{handler for engine_logger in engine_loggers for handler in engine_logger.handlers},
        ]
        for target in filter_targets:
            target.addFilter(error_filter)
        try:
            async with bootstrap_app(application.state.bootstrap, steps):
                if not application.state.web_routes.published:
                    application.state.web_routes.seal()
                await application.state.bootstrap.logger.complete()
                await BannerStep.show_startup_info(application.state.bootstrap)
                yield
        finally:
            application.state.web_routes.unseal()
            for target in filter_targets:
                target.removeFilter(error_filter)

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
    application.state.cache = None
    application.state.database = None
    application.state.monitor = None
    application.state.auth = None
    application.state.security = None
    application.state.tenant = None
    application.state.job = None
    application.state.mq = None
    application.state.websocket = None
    application.state.web_trusted_proxies = ()
    stream_policy = StreamResponsePolicy(settings.engine.value)
    application.state.web_stream_policy = stream_policy
    application.state.web_routes = RouteRegistrar(
        application, access_provider, stream_policy=stream_policy
    )
    application.router.route_class = WebRoute
    web = configuration.web
    # add_middleware 逆序包裹：协议 → CORS → 请求 → 准入 → DI → Monitor → 异常 → GZip → DB → body。
    application.add_middleware(BodyLimitMiddleware, settings=web)
    if "infra" in configuration.modules.enabled:
        from module_infra.framework.logger.infra_access_log_middleware import (
            InfraAccessLogMiddleware,
        )

        application.add_middleware(InfraAccessLogMiddleware)
    application.add_middleware(DatabaseMiddleware)
    application.add_middleware(TenantSelectorMiddleware)
    if web.gzip_enabled:
        application.add_middleware(
            ResponseCompressionMiddleware,
            minimum_size=web.gzip_minimum_size,
            compresslevel=web.gzip_compresslevel,
        )
    application.add_middleware(
        WebExceptionMiddleware, handler=exception_handler, owner=logging_owner
    )
    application.add_middleware(MonitorMiddleware)
    application.add_middleware(DiContextMiddleware)
    application.add_middleware(ReadinessMiddleware)
    application.add_middleware(RequestContextMiddleware, access_log_enabled=web.access_log_enabled)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=web.cors_origins,
        allow_credentials=web.cors_credentials,
        allow_methods=web.cors_methods,
        allow_headers=web.cors_headers,
        expose_headers=web.cors_expose_headers,
        max_age=web.cors_max_age,
    )
    application.add_middleware(HttpProtocolMiddleware)
    exception_handler.register(application)
    application.add_exception_handler(
        SecurityException, SecurityExceptionHandler(exception_handler).handle
    )
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
        logging_owner=logging_owner,
    )
    application.include_router(health_router)
    application.state.web_logging_owner = application.state.bootstrap.logging_owner
    if (
        "module_system" in configuration.modules.packages
        and "system" in configuration.modules.enabled
    ):
        from module_system.router import routers as system_routers

        for router in system_routers:
            application.state.web_routes.include(RouterRegistration(router))
    if (
        "module_infra" in configuration.modules.packages
        and "infra" in configuration.modules.enabled
    ):
        from module_infra.router import routers as infra_routers

        for router in infra_routers:
            application.state.web_routes.include(RouterRegistration(router))
    for registration in routers:
        application.state.web_routes.include(registration)
    return application


app = create_app()
