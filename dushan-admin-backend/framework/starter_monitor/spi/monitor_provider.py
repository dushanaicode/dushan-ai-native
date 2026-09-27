from contextlib import AbstractContextManager
from typing import Protocol

from opentelemetry.context import Context
from opentelemetry.trace import SpanKind


class MonitorProvider(Protocol):
    """跨组件追踪契约；实现负责 span 和上下文传播，消费者不管理其生命周期。"""

    @property
    def enabled(self) -> bool: ...

    def span(
        self,
        name: str,
        attributes=None,
        *,
        kind=SpanKind.INTERNAL,
        parent: Context | None = None,
        start_time=None,
    ) -> AbstractContextManager: ...

    def extract(self, headers) -> Context: ...

    def inject(self, headers: dict[str, str] | None = None) -> dict[str, str]: ...
