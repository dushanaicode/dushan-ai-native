from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar, Mapping

from framework.starter_web.routing.route_policy import RoutePolicy


@dataclass(frozen=True, slots=True)
class RouteDefinition:
    ATTRIBUTE: ClassVar[str] = "__web_routes__"
    BOUND_ATTRIBUTE: ClassVar[str] = "__web_routes_bound__"
    path: str
    methods: tuple[str, ...]
    policy: RoutePolicy | None
    options: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.path and not self.path.startswith("/"):
            raise ValueError("路由 path 必须为空或以 / 开头")
        allowed = {"GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE"}
        if not self.methods or set(self.methods) - allowed:
            raise ValueError("路由必须声明标准大写 HTTP 方法")
        if len(set(self.methods)) != len(self.methods):
            raise ValueError("路由方法不能重复")
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))
