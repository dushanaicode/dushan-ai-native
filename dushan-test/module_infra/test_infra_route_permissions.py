import pytest
from fastapi.routing import APIRoute, _iter_routes_with_context

from framework.starter_web.routing.route_policy import RoutePolicy
from module_infra.framework.websocket.event.cache_monitor_message_event import (
    CacheMonitorMessageEvent,
)
from module_infra.framework.websocket.event.server_monitor_message_event import (
    ServerMonitorMessageEvent,
)
from module_infra.framework.websocket.event.server_usage_message_event import (
    ServerUsageMessageEvent,
)
from module_infra.framework.websocket.handler.cache_monitor_message_handler import (
    CacheMonitorMessageHandler,
)
from module_infra.framework.websocket.handler.server_monitor_message_handler import (
    ServerMonitorMessageHandler,
)
from module_infra.framework.websocket.handler.server_usage_message_handler import (
    ServerUsageMessageHandler,
)
from module_infra.router import routers

pytestmark = pytest.mark.unit

ROUTES = {
    (method, context.path if context else route.path): route.endpoint
    for router in routers
    for route, context in _iter_routes_with_context(router.routes)
    if isinstance(route, APIRoute)
    for method in route.methods
}


def policy(method, path):
    return getattr(ROUTES[(method, "/admin-api/infra" + path)], RoutePolicy.ATTRIBUTE)


@pytest.mark.parametrize(
    "method,path,permissions,mode",
    [
        ("GET", "/file/config/simple-list", ("infra:file:query",), "all"),
        ("POST", "/file/config/test", ("infra:file:config:update",), "all"),
        (
            "GET",
            "/data-source/list-by-status",
            ("infra:data-source:query", "infra:codegen:query"),
            "any",
        ),
    ],
)
def test_corrected_route_permissions(method, path, permissions, mode):
    declared = policy(method, path)
    assert (declared.permissions, declared.permission_mode) == (permissions, mode)


@pytest.mark.parametrize(
    "definition,permission",
    [
        (CacheMonitorMessageEvent.__socket_event__, "infra:cache:get-monitor-info"),
        (CacheMonitorMessageHandler.__socket_handler__, "infra:cache:get-monitor-info"),
        (ServerMonitorMessageEvent.__socket_event__, "infra:server:list"),
        (ServerMonitorMessageHandler.__socket_handler__, "infra:server:list"),
        (ServerUsageMessageEvent.__socket_event__, "infra:server:list"),
        (ServerUsageMessageHandler.__socket_handler__, "infra:server:list"),
    ],
)
def test_websocket_monitor_permissions_match_http_menu_codes(definition, permission):
    assert definition.policy.permissions == (permission,)
