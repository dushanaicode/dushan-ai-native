import math
from time import perf_counter

from framework.starter_monitor.decorators.trace_decorator import TraceDecorator


class PerformanceTrace(TraceDecorator):
    """使用当前应用的阈值分级；装饰器实例不缓存首个应用的配置。"""

    def __init__(
        self,
        operation_name: str = "",
        slow_threshold_ms: float | None = None,
        medium_threshold_ms: float | None = None,
    ):
        for value in (slow_threshold_ms, medium_threshold_ms):
            if value is not None and (
                type(value) not in (int, float) or not math.isfinite(value) or value <= 0
            ):
                raise ValueError("性能阈值必须是有限正数")
        if (
            slow_threshold_ms is not None
            and medium_threshold_ms is not None
            and medium_threshold_ms > slow_threshold_ms
        ):
            raise ValueError("中等阈值不能大于慢操作阈值")
        self.operation_name = operation_name
        self.slow, self.medium = slow_threshold_ms, medium_threshold_ms

    def prepare(self, monitor, span, signature, args, kwargs):
        slow = monitor.settings.performance_slow_ms if self.slow is None else self.slow
        medium = monitor.settings.performance_medium_ms if self.medium is None else self.medium
        if medium > slow:
            raise ValueError("性能装饰器覆盖值与应用阈值冲突")
        return perf_counter(), slow, medium

    def finish(self, monitor, span, state):
        if state is None:
            return
        start, slow, medium = state
        elapsed = (perf_counter() - start) * 1000
        span.set_attributes(
            {
                "performance.duration_ms": elapsed,
                "performance.level": "slow"
                if elapsed > slow
                else "medium"
                if elapsed > medium
                else "fast",
            }
        )
