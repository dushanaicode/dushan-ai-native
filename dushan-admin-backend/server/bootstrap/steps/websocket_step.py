from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_websocket.config.websocket_settings import WebSocketSettings
from framework.starter_websocket.core.socket_protocol_log_filter import SocketProtocolLogFilter
from framework.starter_websocket.core.socket_registry import SocketRegistry
from framework.starter_websocket.core.websocket_runtime import WebSocketRuntime
from framework.starter_websocket.core.websocket_service import WebSocketService
from framework.starter_websocket.enums.socket_transport import SocketTransport
from framework.starter_websocket.exception.socket_exception import SocketException
from framework.starter_websocket.spi.socket_lifecycle_listener import SocketLifecycleListener
from framework.starter_websocket.spi.websocket_ticket_provider import WebSocketTicketProvider
from server.config.application_settings import ApplicationSettings
from server.enums.server_engine_enum import ServerEngineEnum


class WebSocketStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if WebSocketSettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(WebSocketSettings)
        if not settings.enabled:
            yield
            return
        application, security = definitions.application_context, ctx.app.state.security
        if application is None or security is None:
            raise SocketException("configuration")
        tickets = application.container.get_optional(WebSocketTicketProvider)
        if tickets is None:
            raise SocketException("configuration")
        root = ctx.bootstrap_config.get_config(ApplicationSettings)
        workers = (
            root.granian.workers
            if ctx.settings.engine is ServerEngineEnum.GRANIAN
            else root.uvicorn.workers
        )
        if settings.transport is SocketTransport.LOCAL and not root.server.reload and workers != 1:
            raise SocketException("configuration")
        selected = {
            item.component
            for item in application.container.get_binding_diagnostics()
            if item.outcome is BindingOutcomeEnum.SELECTED
        }
        components = [
            component
            for component in definitions.scan_result.get_components()
            if CandidateSelection.qualified_name(component) in selected
        ]
        registry = SocketRegistry(components, security)
        if settings.handler_concurrency > 1 and any(
            not handler.__socket_handler__.parallel for handler in registry.handlers.values()
        ):
            raise SocketException("configuration")
        cache = (
            application.container.get(CacheHandler)
            if settings.transport is SocketTransport.REDIS
            else None
        )
        if cache is not None and ctx.app.state.cache is None:
            raise SocketException("configuration")
        proxies = definitions.configuration.get_config(IpSettings).trusted_proxy_cidrs
        listeners = application.container.get_optional(list[SocketLifecycleListener]) or ()
        runtime = WebSocketRuntime(
            settings,
            application,
            registry,
            security,
            cache,
            tickets,
            application.container.get(MonitorService),
            definitions.translator,
            proxies,
            ctx.logging_owner,
            listeners,
        )
        service = application.container.get(WebSocketService)
        route = None
        primary = None
        SocketProtocolLogFilter.acquire()
        try:
            ctx.app.state.websocket = runtime
            service.runtime = runtime
            await runtime.open()
            route = ctx.app.state.web_routes.register_websocket(
                settings.path,
                runtime.serve,
                authorizer=runtime.authorize,
                policy=RoutePolicy(),
                name="websocket",
            )
            ctx.before_drain.append(runtime.quiesce)
            yield
        except BaseException as error:
            primary = error
        finally:
            if runtime.quiesce in ctx.before_drain:
                ctx.before_drain.remove(runtime.quiesce)
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                runtime.close, "WebSocket 关闭"
            )
            if route is not None:
                ctx.app.state.web_routes.unregister_websocket(route)
            service.runtime = None
            ctx.app.state.websocket = None
            SocketProtocolLogFilter.release()
            CleanupUtils.raise_collected_cleanup_errors(
                "WebSocket 启停失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
