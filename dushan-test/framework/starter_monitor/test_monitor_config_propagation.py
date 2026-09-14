import pytest
from loguru import logger
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import ValidationError

from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.decorators.auto_trace import AutoTrace


@pytest.mark.parametrize(
    "changes",
    [
        {"endpoint": "collector:4317"},
        {"endpoint": "http://user:secret@host:4317"},
        {"endpoint": "http://host:4317/path"},
        {"sample_ratio": float("nan")},
        {"max_queue_size": 0},
        {"max_batch_size": 1024},
        {"sampler": "unknown"},
        {"propagators": ["tracecontext", "tracecontext"]},
        {"propagators": ["baggage"]},
        {"attribute_keys": ["db.statement"]},
        {"attribute_keys": ["password"]},
        {"shutdown_timeout_seconds": 0.1},
        {"performance_slow_ms": 10.0},
    ],
)
def test_invalid_configuration_is_rejected(settings, changes):
    with pytest.raises(ValidationError):
        settings(**changes)


async def test_disabled_does_not_construct_resources(settings, monkeypatch):
    service = MonitorService(settings(enabled=False))
    monkeypatch.setattr(service, "_create_exporter", lambda: pytest.fail("disabled exporter"))
    await service.open(diagnostic_logger=logger)

    @AutoTrace()
    def work():
        return 7

    with service.bind():
        assert work() == 7
        assert (
            service.extract({"traceparent": "00-" + "a" * 32 + "-" + "b" * 16 + "-01"})
            == context.Context()
        )
    assert service._provider is service._pool is service._exporter is None
    await service.close()


@pytest.mark.parametrize(
    "sampler,ratio,count",
    [
        ("always_on", 0.0, 2),
        ("always_off", 1.0, 0),
        ("traceidratio", 0.0, 0),
        ("traceidratio", 1.0, 2),
        ("parentbased_always_on", 1.0, 1),
        ("parentbased_always_off", 0.0, 1),
        ("parentbased_traceidratio", 0.0, 1),
    ],
)
async def test_sdk_sampling_obeys_root_and_remote_parent(settings, sampler, ratio, count):
    service = MonitorService(settings(sampler=sampler, sample_ratio=ratio))
    output = InMemorySpanExporter()
    await service.open(diagnostic_logger=logger, exporter=output)
    try:
        for sampled in ("00", "01"):
            parent = service.extract({"traceparent": f"00-{'a' * 32}-{'b' * 16}-{sampled}"})
            with service.span("sample", parent=parent):
                pass
        await service.flush()
        assert len(output.get_finished_spans()) == count
    finally:
        await service.close()


async def test_explicit_context_cannot_bypass_propagation_filter(settings):
    service = MonitorService(settings())
    output = InMemorySpanExporter()
    await service.open(diagnostic_logger=logger, exporter=output)
    source = trace.SpanContext(
        123, 456, True, trace.TraceFlags(1), trace.TraceState([("vendor", "opaque-private-state")])
    )
    parent = trace.set_span_in_context(trace.NonRecordingSpan(source), context.Context())
    parent = baggage.set_baggage("token", "opaque-baggage-secret", parent)
    try:
        with service.bind(parent):
            with service.span("filtered"):
                assert baggage.get_baggage("token") is None
                assert "tracestate" not in service.inject()
        await service.flush()
        assert "opaque-" not in output.get_finished_spans()[0].to_json()
        assert not output.get_finished_spans()[0].context.trace_state
    finally:
        await service.close()


async def test_propagation_is_bounded_and_baggage_is_allowlisted(settings):
    service = MonitorService(
        settings(propagators=["tracecontext", "baggage"], baggage_keys=["region"])
    )
    output = InMemorySpanExporter()
    await service.open(diagnostic_logger=logger, exporter=output)
    try:
        for header in ("invalid", "00-" + "0" * 32 + "-" + "1" * 16 + "-01", "x" * 5000):
            assert (
                not trace.get_current_span(service.extract({"traceparent": header}))
                .get_span_context()
                .is_valid
            )
        parent = service.extract(
            {
                "traceparent": f"00-{'a' * 32}-{'b' * 16}-01",
                "tracestate": "private=secret",
                "baggage": "region=west,token=opaque-private-token",
            }
        )
        with service.span("request", parent=parent) as span:
            assert baggage.get_baggage("region") == "west"
            assert baggage.get_baggage("token") is None
            carrier = service.inject({"traceparent": "old", "x-caller": "kept"})
            assert carrier["x-caller"] == "kept"
            assert "secret" not in str(carrier) and "tracestate" not in carrier
            assert carrier["baggage"] == "region=west"
            assert span.get_span_context().trace_id == int("a" * 32, 16)
        await service.flush()
        assert output.get_finished_spans()[0].parent.is_remote
        assert "region" not in output.get_finished_spans()[0].attributes
        duplicates = [
            (b"traceparent", f"00-{'a' * 32}-{'b' * 16}-01".encode()),
            (b"TraceParent", b"invalid"),
        ]
        assert not trace.get_current_span(service.extract(duplicates)).get_span_context().is_valid
    finally:
        await service.close()
