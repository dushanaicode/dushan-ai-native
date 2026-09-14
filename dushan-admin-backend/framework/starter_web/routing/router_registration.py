from dataclasses import dataclass

from fastapi import APIRouter

from framework.starter_web.routing.route_policy import RoutePolicy


@dataclass(frozen=True, slots=True)
class RouterRegistration:
    """登记原生 router；policy=None 继承上层声明，最终仍未分类则启动失败。"""

    router: APIRouter
    prefix: str = ""
    policy: RoutePolicy | None = None
