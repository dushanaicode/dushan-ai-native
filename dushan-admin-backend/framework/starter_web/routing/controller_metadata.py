from dataclasses import dataclass
from typing import ClassVar

from framework.starter_web.routing.route_policy import RoutePolicy


@dataclass(frozen=True, slots=True)
class ControllerMetadata:
    ATTRIBUTE: ClassVar[str] = "__web_controller__"
    prefix: str
    tags: tuple[str, ...]
    policy: RoutePolicy | None

    def __post_init__(self) -> None:
        if self.prefix and (not self.prefix.startswith("/") or self.prefix.endswith("/")):
            raise ValueError("控制器 prefix 必须为空或以 / 开头且不以 / 结尾")
