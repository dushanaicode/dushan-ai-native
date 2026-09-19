from framework.starter_di.decorators.components import component
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_web.routing.controller_metadata import ControllerMetadata
from framework.starter_web.routing.route_definition import RouteDefinition
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.web_role_enum import WebRoleEnum


def controller(
    prefix: str = "",
    *,
    tags: tuple[str, ...] = (),
    scope: ComponentScopeEnum | None = None,
    depends_on: tuple[str, ...] = (),
    policy: RoutePolicy | None = None,
):
    """声明可由现有 Scanner/DI 发现的控制器，不创建或缓存应用实例。"""
    metadata = ControllerMetadata(prefix, tuple(tags), policy)

    def decorate(cls):
        if ControllerMetadata.ATTRIBUTE in vars(cls):
            raise ValueError("同一控制器不能重复声明")
        component(WebRoleEnum.CONTROLLER)(cls, scope=scope, depends_on=depends_on)
        setattr(cls, ControllerMetadata.ATTRIBUTE, metadata)
        return cls

    return decorate


def route(
    path: str, *, methods: tuple[str, ...] = ("GET",), policy: RoutePolicy | None = None, **options
):
    """保留原函数及签名，options 直接交给 FastAPI.add_api_route。"""
    definition = RouteDefinition(path, tuple(methods), policy, options)

    def decorate(method):
        definitions = vars(method).get(RouteDefinition.ATTRIBUTE, ())
        setattr(method, RouteDefinition.ATTRIBUTE, (*definitions, definition))
        return method

    return decorate
