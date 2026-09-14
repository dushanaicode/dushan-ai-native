from dataclasses import dataclass
from typing import ClassVar

from starlette.types import Scope


@dataclass(slots=True)
class HttpObservation:
    """本次 HTTP 执行的安全计数，不保存正文、头或原始异常。"""

    KEY: ClassVar[str] = "dushan.http_observation"
    status: int | None = None
    business_code: int | None = None
    body_bytes: int = 0
    complete: bool = False
    disconnected: bool = False
    cancelled: bool = False
    failed: bool = False
    failure_recorded: bool = False

    @classmethod
    def find(cls, scope: Scope) -> "HttpObservation | None":
        return scope.get("state", {}).get(cls.KEY)

    @property
    def outcome(self) -> str:
        if self.failed:
            return "failed_after_response" if self.complete else "interrupted"
        if self.complete:
            return "completed"
        if self.disconnected:
            return "disconnected"
        if self.cancelled:
            return "cancelled"
        return "incomplete"
