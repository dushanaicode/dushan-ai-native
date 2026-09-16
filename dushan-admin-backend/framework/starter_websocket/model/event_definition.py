from pydantic import BaseModel, ConfigDict
from pydantic.dataclasses import dataclass

from framework.starter_web.routing.route_policy import RoutePolicy


@dataclass(
    frozen=True,
    slots=True,
    config=ConfigDict(strict=True, extra="forbid", arbitrary_types_allowed=True),
)
class EventDefinition:
    """下行消息的模型和接收权限；需按接收者数据范围过滤时显式声明 projector。"""

    audience: str
    type: str
    payload: type[BaseModel]
    policy: RoutePolicy
    projector: type | None
