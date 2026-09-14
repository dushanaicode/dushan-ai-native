from threading import Lock

from opentelemetry.trace import INVALID_SPAN_CONTEXT, Span, Status, StatusCode

from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_monitor.core.monitor_attribute_policy import MonitorAttributePolicy
from framework.starter_monitor.core.monitor_diagnostics import MonitorDiagnostics


class MonitorSpan(Span):
    """OpenTelemetry Span 的安全写入边界，观测失败不传播给业务。"""

    def __init__(
        self, span: Span, policy: MonitorAttributePolicy, diagnostics: MonitorDiagnostics, finished
    ):
        self._span, self._policy, self._diagnostics = span, policy, diagnostics
        self._finished = finished
        self._lock = Lock()
        self._ended = False

    def _call(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except BaseException:
            self._diagnostics.increment("span_failures", warn=True)
            return None

    def get_span_context(self):
        result = self._call(self._span.get_span_context)
        return INVALID_SPAN_CONTEXT if result is None else result

    def is_recording(self) -> bool:
        return not self._ended and self._call(self._span.is_recording) is True

    def set_attribute(self, key, value):
        self.set_attributes({key: value})

    def set_attributes(self, attributes):
        self._call(lambda: self._span.set_attributes(self._policy.attributes(attributes)))

    def add_event(self, name, attributes=None, timestamp=None):
        self._call(
            lambda: self._span.add_event(
                self._policy.text(name), self._policy.attributes(attributes), timestamp
            )
        )

    def add_link(self, context, attributes=None):
        # 链接不是当前采集契约，避免把调用方任意TraceState带入导出。
        self._diagnostics.increment("links_ignored")

    def set_status(self, status, description=None):
        self._call(
            lambda: self._span.set_status(
                Status(status.status_code if isinstance(status, Status) else status)
            )
        )

    def update_name(self, name):
        self._call(lambda: self._span.update_name(self._policy.text(name)))

    def record_exception(self, exception, attributes=None, timestamp=None, escaped=False):
        try:
            safe = SafeExceptionDiagnostics.snapshot(exception)
            values = {"exception.type": type(safe).__name__, "exception.escaped": escaped}
            if isinstance(safe, BaseBusinessException):
                values["error.code"] = safe.error_code.code
            self.set_status(StatusCode.ERROR)
            self.add_event("exception", values, timestamp)
        except BaseException:
            self._diagnostics.increment("exception_projection_failures", warn=True)

    def end(self, end_time=None):
        with self._lock:
            if self._ended:
                return
            self._ended = True
        try:
            self._call(self._span.end, end_time)
        finally:
            self._finished(self)
