from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class IpLocation:
    """查询结果区分正常未命中和服务故障，故障摘要不包含远端响应正文。"""

    ip: str
    status: Literal[
        "found", "unknown", "loopback", "private", "link_local", "reserved", "unavailable"
    ]
    location: str | None
    provider: str | None = None
    failures: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.location if self.location is not None else self.status
