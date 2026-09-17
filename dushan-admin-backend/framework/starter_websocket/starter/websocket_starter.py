from loguru import logger

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.decorators.components import starter
from framework.starter_di.enums.binding_outcome_enum import BindingOutcomeEnum
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


@starter
class WebSocketStarter:
    """装配受众/消息策略、票据提供器、传输与端点，统一回收自己的注册。"""

    def __init__(
        self,
        settings: WebSocketSettings,
        application: ApplicationContext,
        service: WebSocketService,
    ):
        self.settings, self.application, self.service = settings, application, service
        self.runtime = self._route = None
        self._routes = None
        self._guard_owned = False

    async def open(
        self,
        *,
        components,
        security,
        cache_available,
        routes,
        translator,
        proxies,
        logging_owner,
        workers,
        reload,
    ):
        if security is None:
            raise SocketException("configuration")
        container = self.application.container
        tickets = container.get_optional(WebSocketTicketProvider)
        if tickets is None:
            raise SocketException("configuration")
        if self.settings.transport is SocketTransport.LOCAL and not reload and workers != 1:
            raise SocketException("configuration")
        selected = {
            item.component
            for item in container.get_binding_diagnostics()
            if item.outcome is BindingOutcomeEnum.SELECTED
        }
        components = [
            item for item in components if CandidateSelection.qualified_name(item) in selected
        ]
        registry = SocketRegistry(components, security)
        if self.settings.handler_concurrency > 1 and any(
            not handler.__socket_handler__.parallel for handler in registry.handlers.values()
        ):
            raise SocketException("configuration")
        cache = (
            container.get(CacheHandler)
            if self.settings.transport is SocketTransport.REDIS
            else None
        )
        if cache is not None and cache_available is None:
            raise SocketException("configuration")
        listeners = container.get_optional(list[SocketLifecycleListener]) or ()
        self.runtime = WebSocketRuntime(
            self.settings,
            self.application,
            registry,
            security,
            cache,
            tickets,
            container.get(MonitorService),
            translator,
            proxies,
            logging_owner,
            listeners,
        )
        self.service.runtime = self.runtime
        self._routes = routes
        SocketProtocolLogFilter.acquire()
        self._guard_owned = True
        await self.runtime.open()
        self._route = routes.register_websocket(
            self.settings.path,
            self.runtime.serve,
            authorizer=self.runtime.authorize,
            policy=RoutePolicy(),
            name="websocket",
        )
        logger.info(
            "【WebSocketStarter 】端点登记完成：path={} transport={}，处理器 {} 个",
            self.settings.path,
            self.settings.transport.value,
            len(registry.handlers),
        )
        return self.runtime

    async def close(self):
        try:
            if self.runtime is not None:
                await self.runtime.close()
        finally:
            try:
                if self._route is not None:
                    self._routes.unregister_websocket(self._route)
                    self._route = None
            finally:
                self.service.runtime = None
                if self._guard_owned:
                    SocketProtocolLogFilter.release()
                    self._guard_owned = False
        logger.info("【WebSocketStarter 】WebSocket 资源已关闭")
