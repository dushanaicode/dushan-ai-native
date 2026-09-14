import pytest
from fastapi import Request
from loguru import logger
from opentelemetry import context, trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.util.trace_context_utils import TraceContextUtils
from framework.starter_monitor.util.tracer_utils import TracerUtils

pytestmark = pytest.mark.unit

TRACE = "0123456789abcdef0123456789abcdef"
SPAN = "0123456789abcdef"


def request(headers=()):
    return Request(
        {"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": headers}
    )


def saved_context():
    span = NonRecordingSpan(
        SpanContext(int(TRACE, 16), int(SPAN, 16), is_remote=False, trace_flags=TraceFlags(1))
    )
    return trace.set_span_in_context(span, context.Context())


def test_w3c_trace_headers_are_parsed_and_local_id_is_stable():
    req = request([(b"traceparent", f"00-{TRACE}-{SPAN}-01".encode())])
    assert TraceContextUtils.extract_trace_from_request(req)["trace_id"] == TRACE
    assert TracerUtils.get_trace_id(req) == TRACE
    bad = request([(b"x-trace-id", b"not-trusted"), (b"traceparent", b"malformed")])
    first = TracerUtils.get_trace_id(bad)
    assert len(first) == 32 and first != "not-trusted"
    assert TracerUtils.get_trace_id(bad) == first
    assert TracerUtils.get_trace_id() is None


def test_trace_binding_and_headers_restore_after_failures():
    previous = context.get_current()

    def inspect():
        assert TracerUtils.get_trace_id() == TRACE
        headers = TraceContextUtils.inject_trace_to_headers({"accept": "application/json"})
        assert headers["traceparent"] == f"00-{TRACE}-{SPAN}-01"
        assert headers["accept"] == "application/json"
        assert TraceContextUtils.extract_trace_from_request(request())["trace_id"] is None
        raise RuntimeError("expected")

    with pytest.raises(RuntimeError):
        TraceContextUtils.execute_with_context(saved_context(), inspect)
    assert context.get_current() is previous


async def test_async_trace_binding_restores_context_on_failure():
    previous = context.get_current()

    async def fail():
        assert TracerUtils.get_span_id() == SPAN
        raise RuntimeError("expected")

    with pytest.raises(RuntimeError):
        await TraceContextUtils.execute_async_with_context(saved_context(), fail)
    assert context.get_current() is previous


async def test_span_error_recording_does_not_send_raw_exception_to_sdk(settings):
    monitor = MonitorService(settings())
    exporter = InMemorySpanExporter()
    await monitor.open(diagnostic_logger=logger, exporter=exporter)
    try:
        with monitor.bind():
            with TraceContextUtils.start_span("manual") as span:
                TraceContextUtils.record_error(
                    span, ValueError("opaque-private-value"), {"access_token": "raw-token"}
                )
            raw = monitor._tracer.start_span("unprotected")
            try:
                with pytest.raises(TypeError, match="安全 Span"):
                    TraceContextUtils.record_error(raw, ValueError("foreign-secret"))
            finally:
                raw.end()
        assert await monitor.flush()
        spans = exporter.get_finished_spans()
        output = "".join(span.to_json() for span in spans)
        assert all(
            secret not in output
            for secret in ("opaque-private-value", "raw-token", "foreign-secret")
        )
        recorded = next(span for span in spans if span.name == "manual")
        assert len(recorded.events) == 1 and recorded.events[0].name == "exception"
        assert recorded.status.status_code is trace.StatusCode.ERROR
    finally:
        await monitor.close()


async def test_custom_spans_use_the_current_application_and_record_failure_once(
    settings, monkeypatch
):
    provider = trace.get_tracer_provider()
    first, second = (
        MonitorService(settings(service_name="first")),
        MonitorService(settings(service_name="second")),
    )
    first_exporter, second_exporter = InMemorySpanExporter(), InMemorySpanExporter()
    await first.open(diagnostic_logger=logger, exporter=first_exporter)
    await second.open(diagnostic_logger=logger, exporter=second_exporter)

    def unexpected_global_provider(*args, **kwargs):
        raise AssertionError("Custom spans must use the application's provider")

    monkeypatch.setattr(trace, "get_tracer", unexpected_global_provider)
    failure = ValueError("opaque-sensitive-ticket")
    try:
        with first.bind():
            with TracerUtils.custom_span("first") as first_span:
                with second.bind():
                    with TracerUtils.custom_span("second") as second_span:
                        assert (
                            first_span.get_span_context().trace_id
                            != second_span.get_span_context().trace_id
                        )
                assert MonitorService.current() is first
                with pytest.raises(ValueError) as caught:
                    with TracerUtils.custom_span("failed"):
                        raise failure
                assert caught.value is failure
                assert trace.get_current_span() is first_span
        assert await first.flush() and await second.flush()
        a, b = first_exporter.get_finished_spans(), second_exporter.get_finished_spans()
        assert {span.name for span in a} == {"first", "failed"}
        assert [span.name for span in b] == ["second"]
        failed = next(span for span in a if span.name == "failed")
        assert len(failed.events) == 1 and failed.events[0].name == "exception"
        assert "opaque-sensitive-ticket" not in "".join(span.to_json() for span in a)
        assert trace.get_tracer_provider() is provider
    finally:
        await first.close()
        await second.close()


def test_custom_span_preserves_exception_identity():
    error = ValueError("original")
    with pytest.raises(ValueError) as caught:
        with TracerUtils.custom_span("operation"):
            raise error
    assert caught.value is error
