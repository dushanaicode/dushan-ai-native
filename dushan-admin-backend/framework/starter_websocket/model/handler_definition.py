from pydantic import BaseModel, ConfigDict
from pydantic.dataclasses import dataclass

from framework.starter_web.routing.route_policy import RoutePolicy


@dataclass(
    frozen=True,
    slots=True,
    config=ConfigDict(strict=True, extra="forbid", arbitrary_types_allowed=True),
)
class HandlerDefinition:
    audience: str
    type: str
    payload: type[BaseModel]
    policy: RoutePolicy
    parallel: bool = False
