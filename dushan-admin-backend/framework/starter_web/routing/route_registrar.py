import inspect
from collections.abc import Callable, Iterable
from functools import partial, update_wrapper

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute, _iter_routes_with_context

from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_web.routing.authenticated_websocket_route import AuthenticatedWebSocketRoute
from framework.starter_web.routing.controller_metadata import ControllerMetadata
from framework.starter_web.routing.published_routes import PublishedRoutes
from framework.starter_web.routing.route_audit import RouteAudit
from framework.starter_web.routing.route_definition import RouteDefinition
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.route_snapshot import RouteSnapshot
from framework.starter_web.routing.router_registration import RouterRegistration
from framework.starter_web.routing.web_route import WebRoute


class RouteRegistrar:
    """将已选择的定义发布到一个应用，所有请求参数与依赖仍由 FastAPI 处理。"""

    def __init__(
        self, app: FastAPI, access_provider: Callable | None = None, *, stream_policy=None
    ) -> None:
        self.app = app
        self.access_provider = access_provider
        self.stream_policy = stream_policy
        self.policy_validator = None
        self._sealed = False
        self._declarations = None
        self._host_routes = tuple(app.routes)
        self._socket_routes = {}

    @property
    def published(self) -> bool:
        return self._sealed

    def include(self, registration: RouterRegistration) -> None:
        if self._sealed:
            raise RuntimeError("Web 路由已经发布，显式注册必须在应用启动前完成")
        protected = registration.policy is not None and registration.policy.requires_identity
        if protected and self.access_provider is None:
            raise ValueError("受保护路由缺少授权提供者")
        if protected and any(
            not isinstance(route, APIRoute)
            for route, _ in _iter_routes_with_context(registration.router.routes)
        ):
            raise ValueError(
                "受保护 router 只支持 HTTP APIRoute；Mount/WebSocket 需要宿主独立授权接入"
            )
        candidate = APIRouter(route_class=WebRoute)
        if registration.policy is not None:
            registration.policy(candidate)
        candidate.include_router(
            registration.router,
            prefix=registration.prefix,
        )
        RouteAudit.validate([*self.app.routes, *candidate.routes])
        self.app.include_router(candidate)

    def seal(self) -> None:
        if self._sealed:
            raise RuntimeError("Web 路由已经发布")
        RouteAudit.validate(self.app.routes)
        snapshot = RouteSnapshot(
            self.access_provider, self._host_routes, self.stream_policy, self.policy_validator
        ).build(self.app.routes, getattr(self.app.router, RoutePolicy.ATTRIBUTE, None))
        RouteAudit.validate(snapshot)
        self._declarations = self.app.router.routes
        self.app.router.routes = PublishedRoutes(snapshot)
        self.app.router._mark_routes_changed()
        self.app.openapi_schema = None
        self._sealed = True

    def register_websocket(self, path, endpoint, *, authorizer, policy, name=None):
        """在正式发布前登记受保护 WebSocket；同样审计重复、遮蔽及最终策略。"""
        if self._sealed:
            raise RuntimeError("Web 路由已经发布")
        route = AuthenticatedWebSocketRoute(
            path, endpoint, authorizer=authorizer, policy=policy, name=name
        )
        RouteAudit.validate([*self.app.routes, route])
        self.app.router.routes.append(route)
        self.app.router._mark_routes_changed()
        self._socket_routes[id(route)] = route
        return route

    def unregister_websocket(self, route):
        """只撤销本注册器持有的声明；宿主必须先完成 unseal。"""
        if self._sealed or self._socket_routes.get(id(route)) is not route:
            raise RuntimeError("WebSocket 路由不属于当前未发布注册器")
        del self._socket_routes[id(route)]
        self.app.router.routes.remove(route)
        self.app.router._mark_routes_changed()

    def unseal(self) -> None:
        if self._sealed:
            self.app.router.routes = self._declarations
            self._declarations = None
            self.app.router._mark_routes_changed()
        self._sealed = False

    def register_controllers(self, controllers: Iterable[type]) -> None:
        candidate = APIRouter(route_class=WebRoute)
        for cls in controllers:
            metadata = vars(cls)[ControllerMetadata.ATTRIBUTE]
            controller_policy = None
            for base in reversed(cls.__mro__):
                inherited = vars(base).get(ControllerMetadata.ATTRIBUTE)
                if inherited is not None:
                    controller_policy = RoutePolicy.resolve(controller_policy, inherited.policy)
            dependency = DiDependency(cls)
            # MRO 按 Python 覆盖规则展开；覆盖未装饰方法即撤销继承的路由。
            members = {}
            for base in reversed(cls.__mro__):
                members.update(vars(base))
            for method in members.values():
                if isinstance(method, (classmethod, staticmethod)) and (
                    getattr(method, RouteDefinition.ATTRIBUTE, ())
                    or getattr(method.__func__, RouteDefinition.ATTRIBUTE, ())
                ):
                    raise TypeError(
                        "控制器路由不支持 staticmethod/classmethod，请使用实例方法或原生 router"
                    )
                if not inspect.isfunction(method):
                    continue
                for definition in vars(method).get(RouteDefinition.ATTRIBUTE, ()):
                    options = dict(definition.options)
                    dependencies = list(options.pop("dependencies", ()))
                    method_policy = getattr(method, RoutePolicy.ATTRIBUTE, None)
                    if (
                        definition.policy is not None
                        and method_policy is not None
                        and definition.policy != method_policy
                    ):
                        raise ValueError("控制器方法的访问声明冲突")
                    policy = definition.policy if definition.policy is not None else method_policy
                    policy = RoutePolicy.resolve(controller_policy, policy)
                    for http_method in definition.methods:
                        endpoint = self._endpoint(method, dependency)
                        if policy is not None:
                            policy(endpoint)
                        candidate.add_api_route(
                            metadata.prefix + definition.path,
                            endpoint,
                            methods=[http_method],
                            tags=list(metadata.tags),
                            dependencies=dependencies,
                            **options,
                        )
        if candidate.routes:
            self.include(RouterRegistration(candidate))

    @staticmethod
    def _endpoint(method: Callable, dependency: DiDependency) -> Callable:
        signature = inspect.signature(method, eval_str=True)
        parameters = list(signature.parameters.values())
        if (
            not parameters
            or parameters[0].name != "self"
            or any(
                parameter.kind
                in {
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                }
                for parameter in parameters
            )
        ):
            raise TypeError("控制器路由必须是 self 实例方法并使用明确的具名参数")
        endpoint = update_wrapper(partial(method), method)
        setattr(endpoint, RouteDefinition.BOUND_ATTRIBUTE, True)
        endpoint.__signature__ = signature.replace(
            parameters=[
                *parameters[1:],
                parameters[0].replace(
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    annotation=object,
                    default=Depends(dependency),
                ),
            ]
        )
        return endpoint
