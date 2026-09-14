from time import time_ns

from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_protection.core.protection_event import ProtectionEvent


class MonitorProtectionObserver:
    """显式可选适配；核心仅认识事件回调，不导入 Monitor 或创建另一套追踪器。"""

    def __init__(self, monitor: MonitorService) -> None:
        self.monitor = monitor

    def __call__(self, event: ProtectionEvent) -> None:
        ended = time_ns()
        # 使用当前 Monitor 已允许的字段，事件名仅含框架定义的有限分类。
        with self.monitor.span(
            f"protection.{event.feature}.{event.action}.{event.outcome}",
            {
                "code.function.name": f"{event.feature}.{event.action}",
                "performance.duration_ms": event.elapsed_ms,
            },
            start_time=ended - int(event.elapsed_ms * 1_000_000),
        ) as span:
            span.end(ended)
