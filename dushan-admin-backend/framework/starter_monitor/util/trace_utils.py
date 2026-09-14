from opentelemetry import trace

from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.util.trace_context_utils import TraceContextUtils


class TraceUtils:
    """供MQ、WebSocket等消费者读取真实链路标识，异常记录交给所属应用安全入口。"""

    @staticmethod
    def get_current_trace_id() -> str | None:
        return TraceContextUtils.get_current_trace_info()["trace_id"]

    @staticmethod
    def get_current_span_id() -> str | None:
        return TraceContextUtils.get_current_trace_info()["span_id"]

    @staticmethod
    def get_current_trace_flags() -> str | None:
        current = trace.get_current_span().get_span_context()
        return format(int(current.trace_flags), "02x") if current.is_valid else None

    @staticmethod
    def on_error(error, span=None):
        monitor = MonitorService.current()
        if span is not None:
            try:
                safe = SafeExceptionDiagnostics.snapshot(error)
                attributes = {"exception.type": type(safe).__name__[:128]}
                if isinstance(safe, BaseBusinessException):
                    attributes["error.code"] = safe.error_code.code
                span.set_status(trace.StatusCode.ERROR)
                span.add_event("exception", attributes)
            except BaseException:
                if monitor is not None:
                    monitor.diagnostics.increment("exception_projection_failures", warn=True)
        elif monitor is not None:
            monitor.on_error(error)
