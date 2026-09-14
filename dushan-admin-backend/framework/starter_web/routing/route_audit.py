import re
from collections.abc import Sequence

from fastapi.routing import APIRoute, _iter_routes_with_context
from starlette.routing import BaseRoute, Match, Mount, Route, WebSocketRoute

from framework.starter_web.routing.route_definition import RouteDefinition


class RouteAudit:
    """只读核对当前 FastAPI 版本的最终路径，不实现第二套路由匹配器。"""

    @staticmethod
    def validate(routes: Sequence[BaseRoute]) -> None:
        operation_ids: set[str] = set()
        documented_paths: dict[str, str] = {}
        documented_operations: set[tuple[str, str]] = set()
        previous = []
        for route, context in _iter_routes_with_context(routes):
            if isinstance(route, APIRoute):
                if getattr(route.endpoint, RouteDefinition.ATTRIBUTE, ()) and not getattr(
                    route.endpoint, RouteDefinition.BOUND_ATTRIBUTE, False
                ):
                    raise ValueError("@route 声明必须由控制器注册器处理，不能作为裸端点公开")
            effective = (
                route
                if context is None
                else (context if isinstance(route, APIRoute) else context.starlette_route)
            )
            if isinstance(route, Mount):
                methods = {"*", "WEBSOCKET"}
            elif isinstance(route, WebSocketRoute):
                methods = {"WEBSOCKET"}
            elif isinstance(route, Route):
                methods = effective.methods or {"*"}
            else:
                raise TypeError(f"未支持的路由类型：{type(route).__name__}")
            identity = re.sub(r"\(\?P<[^>]+>", "(?:", effective.path_regex.pattern)
            for earlier, earlier_methods, is_mount, earlier_identity in previous:
                shared = RouteAudit._shared_methods(methods, earlier_methods)
                if not shared:
                    continue
                if identity == earlier_identity:
                    raise ValueError(f"重复路由：{effective.path} 与 {earlier.path}")
                if is_mount and (
                    not earlier.path or effective.path.startswith(earlier.path.rstrip("/") + "/")
                ):
                    raise ValueError(f"路由被前序 Mount 遮蔽：{effective.path} <- {earlier.path}")
                if not effective.param_convertors and not isinstance(route, Mount):
                    for method in shared:
                        protocol = "websocket" if method == "WEBSOCKET" else "http"
                        match, _ = earlier.matches(
                            {
                                "type": protocol,
                                "path": effective.path,
                                "root_path": "",
                                "method": method,
                            }
                        )
                        if match is Match.FULL:
                            raise ValueError(
                                f"路由被前序路径遮蔽：{effective.path} <- {earlier.path}"
                            )
            previous.append((effective, methods, isinstance(route, Mount), identity))
            if isinstance(route, APIRoute) and effective.include_in_schema:
                template = re.sub(r"\{[^{}]+\}", "{}", effective.path_format)
                if (
                    template in documented_paths
                    and documented_paths[template] != effective.path_format
                ):
                    raise ValueError(
                        f"OpenAPI 路径模板冲突：{effective.path_format} 与 {documented_paths[template]}"
                    )
                documented_paths[template] = effective.path_format
                for method in methods:
                    key = method, effective.path_format
                    if key in documented_operations:
                        raise ValueError(f"OpenAPI 操作冲突：{method} {effective.path_format}")
                    documented_operations.add(key)
                if len(effective.methods) > 1:
                    raise ValueError(
                        "OpenAPI 每个操作需要唯一标识，请用原生装饰器分别声明 HTTP 方法"
                    )
                if effective.unique_id in operation_ids:
                    raise ValueError(f"重复 OpenAPI operationId：{effective.unique_id}")
                operation_ids.add(effective.unique_id)

    @staticmethod
    def _shared_methods(first: set[str], second: set[str]) -> set[str]:
        # 原生 ASGI Route 可接受任意 HTTP 方法；Mount 同时接受 HTTP/WebSocket。
        shared = first & second
        if "*" in first:
            shared |= second - {"WEBSOCKET"}
        if "*" in second:
            shared |= first - {"WEBSOCKET"}
        return shared
