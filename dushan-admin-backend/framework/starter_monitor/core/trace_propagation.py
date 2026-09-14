from collections.abc import Mapping

from opentelemetry import baggage, trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import Context
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceState
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from framework.starter_monitor.config.monitor_settings import MonitorSettings
from framework.starter_monitor.core.monitor_attribute_policy import MonitorAttributePolicy
from framework.starter_monitor.core.monitor_diagnostics import MonitorDiagnostics


class TracePropagation:
    """只在空上下文解析标准传播头；baggage不进入Span，TraceState不采集。"""

    def __init__(self, settings: MonitorSettings, diagnostics: MonitorDiagnostics):
        self.settings, self.diagnostics = settings, diagnostics
        self._trace = TraceContextTextMapPropagator()
        self._baggage = W3CBaggagePropagator()
        self._policy = MonitorAttributePolicy(settings)

    def extract(self, headers) -> Context:
        pairs = headers.items() if isinstance(headers, Mapping) else headers
        carrier = {}
        size = 0
        for name, value in pairs:
            key = name.decode("latin-1") if isinstance(name, bytes) else name
            key = key.lower()
            if key not in {"traceparent", "baggage"}:
                continue
            value = value.decode("latin-1") if isinstance(value, bytes) else value
            size += len(key.encode()) + len(value.encode())
            if key in carrier or size > self.settings.max_propagation_bytes:
                self.diagnostics.increment("invalid_contexts")
                return Context()
            carrier[key] = value
        result = Context()
        if "tracecontext" in self.settings.propagators:
            parsed = self._trace.extract(carrier, context=Context())
            parent = trace.get_current_span(parsed).get_span_context()
            if parent.is_valid:
                parent = SpanContext(
                    parent.trace_id, parent.span_id, True, parent.trace_flags, TraceState()
                )
                result = trace.set_span_in_context(NonRecordingSpan(parent), result)
            elif "traceparent" in carrier:
                self.diagnostics.increment("invalid_contexts")
        if "baggage" in self.settings.propagators:
            parsed = self._baggage.extract(carrier, context=Context())
            for key in self.settings.baggage_keys:
                value = baggage.get_baggage(key, parsed)
                if value is not None:
                    result = baggage.set_baggage(key, self._policy.text(value), result)
        return result

    def inject(self, parent: Context, headers: dict[str, str] | None = None) -> dict[str, str]:
        parent = self.clean_context(parent)
        result = {
            key: value
            for key, value in (headers or {}).items()
            if key.lower() not in {"traceparent", "tracestate", "baggage"}
        }
        if "tracecontext" in self.settings.propagators:
            self._trace.inject(result, context=parent)
        if "baggage" in self.settings.propagators:
            allowed = Context()
            for key in self.settings.baggage_keys:
                value = baggage.get_baggage(key, parent)
                if type(value) is str:
                    allowed = baggage.set_baggage(key, self._policy.text(value), allowed)
            self._baggage.inject(result, context=allowed)
        if (
            sum(
                len(key.encode()) + len(value.encode())
                for key, value in result.items()
                if key.lower() in {"traceparent", "baggage"}
            )
            > self.settings.max_propagation_bytes
        ):
            result.pop("baggage", None)
            self.diagnostics.increment("propagation_dropped")
        return result

    def clean_context(self, parent: Context) -> Context:
        """显式Context入口也遵循同一边界，不允许绕过extract携带TraceState或额外baggage。"""
        result = Context()
        span = trace.get_current_span(parent).get_span_context()
        if span.is_valid:
            span = SpanContext(
                span.trace_id, span.span_id, span.is_remote, span.trace_flags, TraceState()
            )
            result = trace.set_span_in_context(NonRecordingSpan(span), result)
        if "baggage" in self.settings.propagators:
            for key in self.settings.baggage_keys:
                value = baggage.get_baggage(key, parent)
                if type(value) is str:
                    result = baggage.set_baggage(key, self._policy.text(value), result)
        return result
