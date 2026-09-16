from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from framework.starter_web.routing.route_policy import RoutePolicy


@dataclass(frozen=True, slots=True, config=ConfigDict(strict=True, extra="forbid"))
class AudienceDefinition:
    """由业务模块声明接入、发送及显式全局工作负载权限。"""

    key: str
    policy: RoutePolicy
    send_policy: RoutePolicy
    workload_capability: str | None
    allow_global_targets: bool
