import pytest
from fastapi import Request
from opentelemetry import context, trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from framework.common.utils.monitor.tracer_utils import TracerUtils
from framework.common.utils.trace.trace_context_utils import TraceContextUtils

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


def test_span_error_recording_does_not_send_raw_exception_to_sdk():
    class RecordingSpan:
        def __init__(self):
            self.events = []
            self.status = None

        def is_recording(self):
            return True

        def set_status(self, status):
            self.status = status

        def add_event(self, name, attributes):
            self.events.append((name, attributes))

    span = RecordingSpan()
    original = ValueError("password=private-value")
    TraceContextUtils.record_error(span, original, {"access_token": "raw-token"})
    output = repr(span.events)
    assert "private-value" not in output and "raw-token" not in output
    assert span.events[0][0] == "exception" and span.status.is_ok is False


def test_custom_span_preserves_exception_identity():
    error = ValueError("original")
    with pytest.raises(ValueError) as caught:
        with TracerUtils.custom_span("operation"):
            raise error
    assert caught.value is error
