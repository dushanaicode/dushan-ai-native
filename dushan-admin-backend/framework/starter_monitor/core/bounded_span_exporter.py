from threading import Lock
from time import monotonic

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from framework.starter_monitor.core.monitor_diagnostics import MonitorDiagnostics
from framework.starter_monitor.core.sdk_log_guard import SdkLogGuard


class BoundedSpanExporter(SpanExporter):
    """复用SDK导出协议；预算不足时丢弃剩余批次，不启动注定超过预算的RPC。"""

    def __init__(self, exporter: SpanExporter, timeout: float, diagnostics: MonitorDiagnostics):
        self.exporter, self.timeout, self.diagnostics = exporter, timeout, diagnostics
        self._lock = Lock()
        self._deadline: float | None = None
        self._pending = 0
        self._accepting = True
        self._closed = False
        self._closing = False
        self._shutdown_complete = False

    def reserve(self, limit: int) -> bool:
        with self._lock:
            accepted = self._accepting and self._pending < limit
            if accepted:
                self._pending += 1
        if not accepted:
            self.diagnostics.increment("dropped_spans", warn=True)
        return accepted

    def release(self, count: int) -> None:
        with self._lock:
            self._pending -= count

    @property
    def pending(self) -> int:
        with self._lock:
            return self._pending

    def begin_drain(self, seconds: float, *, closing: bool = False) -> None:
        with self._lock:
            self._accepting = False
            deadline = monotonic() + max(0, seconds)
            self._deadline = deadline if self._deadline is None else min(self._deadline, deadline)
            self._closing |= closing

    def resume(self) -> None:
        with self._lock:
            if not self._closing:
                self._deadline = None
                self._accepting = not self._closed

    def export(self, spans):
        try:
            with self._lock:
                expired = self._deadline is not None and monotonic() + self.timeout > self._deadline
            if expired:
                self.diagnostics.increment("budget_dropped_spans", len(spans), warn=True)
                return SpanExportResult.FAILURE
            with SdkLogGuard.quiet():
                result = self.exporter.export(spans)
            if result is SpanExportResult.SUCCESS:
                self.diagnostics.increment("exported_spans", len(spans))
            else:
                self.diagnostics.increment("export_failures", warn=True)
            return result
        except BaseException:
            self.diagnostics.increment("export_failures", warn=True)
            return SpanExportResult.FAILURE
        finally:
            self.release(len(spans))

    def shutdown(self, timeout_millis: float = 30000) -> None:
        with self._lock:
            if self._shutdown_complete:
                return
            self._closed = True
            self._accepting = False
        with SdkLogGuard.quiet():
            self.exporter.shutdown()
        self._shutdown_complete = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
