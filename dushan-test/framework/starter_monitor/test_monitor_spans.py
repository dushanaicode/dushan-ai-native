import asyncio
import inspect

import pytest
from loguru import logger
from opentelemetry import context, propagate, trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.decorators.auto_trace import AutoTrace
from framework.starter_monitor.decorators.biz_trace import BizTrace
from framework.starter_monitor.decorators.performance_trace import PerformanceTrace


async def test_real_spans_return_signature_parentage_and_error(settings):
    monitor = MonitorService(settings(capture_business_ids=True))
    exporter = InMemorySpanExporter()
    await monitor.open(diagnostic_logger=logger, exporter=exporter)

    def function(identifier: int, /, *, value: int = 3) -> int:
        return identifier + value

    wrapped = AutoTrace(biz_id_param="identifier")(function)
    assert inspect.signature(wrapped) == inspect.signature(function)
    failure = ValueError("opaque-sensitive-ticket")

    @BizTrace(operation_name="business", id_expr="identifier", type_expr="'test'")
    async def business(identifier):
        assert wrapped(identifier) == 3
        raise failure

    try:
        with monitor.bind():
            before = trace.get_current_span()
            with pytest.raises(ValueError) as error:
                await business(0)
            assert error.value is failure
            assert trace.get_current_span() is before
        assert await monitor.flush()
        spans = exporter.get_finished_spans()
        child, parent = spans
        assert child.parent.span_id == parent.context.span_id
        assert child.attributes["biz.id"] == parent.attributes["biz.id"] == 0
        assert parent.status.status_code is trace.StatusCode.ERROR
        assert "opaque-sensitive-ticket" not in str([span.to_json() for span in spans])
    finally:
        await monitor.close()


async def test_cancel_and_instrumentation_errors_preserve_business(settings, monkeypatch):
    monitor = MonitorService(settings())
    exporter = InMemorySpanExporter()
    await monitor.open(diagnostic_logger=logger, exporter=exporter)

    @AutoTrace()
    async def cancel():
        raise asyncio.CancelledError("opaque-cancel-secret")

    try:
        with monitor.bind():
            original = context.get_current()
            with pytest.raises(asyncio.CancelledError):
                await cancel()
            assert context.get_current() is original
            monkeypatch.setattr(
                monitor._tracer,
                "start_span",
                lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("SDK-secret")),
            )

            @AutoTrace()
            def works():
                return 42

            assert works() == 42
            assert context.get_current() is original
        await monitor.flush()
        assert exporter.get_finished_spans()[0].events[0].name == "cancelled"
        assert monitor.get_statistics()["span_start_failures"] == 1
    finally:
        await monitor.close()


async def test_multiple_instances_do_not_publish_global_sdk_state(settings):
    provider, propagator = trace.get_tracer_provider(), propagate.get_global_textmap()
    a, b = (
        MonitorService(settings(service_name="one")),
        MonitorService(settings(service_name="two")),
    )
    ae, be = InMemorySpanExporter(), InMemorySpanExporter()
    await a.open(diagnostic_logger=logger, exporter=ae)
    await b.open(diagnostic_logger=logger, exporter=be)

    @AutoTrace()
    def work():
        return trace.get_current_span().get_span_context().trace_id

    try:
        with a.bind():
            first = work()
            with b.bind():
                second = work()
            assert MonitorService.current() is a
        assert first != second
        await a.close()
        with b.bind():
            work()
        await b.flush()
        assert len(ae.get_finished_spans()) == 1
        assert len(be.get_finished_spans()) == 2
        assert ae.get_finished_spans()[0].resource.attributes["service.name"] == "one"
        assert be.get_finished_spans()[0].resource.attributes["service.name"] == "two"
        assert trace.get_tracer_provider() is provider
        assert propagate.get_global_textmap() is propagator
    finally:
        await a.close()
        await b.close()


async def test_performance_thresholds_are_per_application(settings):
    @PerformanceTrace()
    async def work():
        await asyncio.sleep(0.01)

    for slow, level in [(1.0, "slow"), (1000.0, "fast")]:
        service = MonitorService(settings(performance_medium_ms=slow / 2, performance_slow_ms=slow))
        exporter = InMemorySpanExporter()
        await service.open(diagnostic_logger=logger, exporter=exporter)
        try:
            with service.bind():
                await work()
            await service.flush()
            assert exporter.get_finished_spans()[0].attributes["performance.level"] == level
        finally:
            await service.close()


@pytest.mark.parametrize("decorator", [AutoTrace, BizTrace, PerformanceTrace])
def test_generator_and_duplicate_decoration_are_explicit(decorator):
    def generator():
        yield 1

    async def async_generator():
        yield 1

    for function in (generator, async_generator):
        with pytest.raises(TypeError, match="生成器"):
            decorator()(function)
    with pytest.raises(ValueError, match="一个追踪"):
        decorator()(AutoTrace()(lambda: 1))
