from threading import Lock

from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from framework.starter_monitor.config.monitor_settings import MonitorSettings
from framework.starter_monitor.core.bounded_span_exporter import BoundedSpanExporter


class MonitorSpanProcessor(SpanProcessor):
    """SDK批处理前设置容量闸门，保留队列满和预算丢弃的应用级诊断。"""

    def __init__(self, exporter: BoundedSpanExporter, settings: MonitorSettings):
        self.exporter, self.settings = exporter, settings
        self._admission = Lock()
        self._batch = BatchSpanProcessor(
            exporter,
            max_queue_size=settings.max_queue_size,
            schedule_delay_millis=settings.schedule_delay_millis,
            max_export_batch_size=settings.max_batch_size,
            export_timeout_millis=settings.export_timeout_seconds * 1000,
            meter_provider=NoOpMeterProvider(),
        )

    def on_start(self, span, parent_context=None):
        pass

    def on_end(self, span):
        if not span.context.trace_flags.sampled:
            return
        with self._admission:
            if self.exporter.reserve(self.settings.max_queue_size):
                try:
                    self._batch.on_end(span)
                except BaseException:
                    self.exporter.release(1)
                    self.exporter.diagnostics.increment("processor_failures", warn=True)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        before = self.exporter.diagnostics.snapshot()
        # SDK当前force_flush忽略timeout且可追逐新记录；本轮flush只排空已接纳集合。
        with self._admission:
            self.exporter.begin_drain(timeout_millis / 1000)
        try:
            self._batch.force_flush(timeout_millis)
        finally:
            self.exporter.resume()
        after = self.exporter.diagnostics.snapshot()
        return all(
            after.get(key, 0) == before.get(key, 0)
            for key in ("export_failures", "budget_dropped_spans")
        )

    def shutdown(self):
        with self._admission:
            self.exporter.begin_drain(self.settings.shutdown_timeout_seconds, closing=True)
        self._batch.shutdown()

    def begin_shutdown(self):
        with self._admission:
            self.exporter.begin_drain(self.settings.shutdown_timeout_seconds, closing=True)
