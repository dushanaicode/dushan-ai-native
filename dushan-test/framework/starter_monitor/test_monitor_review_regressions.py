import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from loguru import logger
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.core.monitor_span_processor import MonitorSpanProcessor
from framework.starter_monitor.decorators.auto_trace import AutoTrace
from framework.starter_monitor.decorators.biz_trace import BizTrace
from framework.starter_monitor.exception.monitor_exception import MonitorException


@pytest.mark.parametrize("error", [asyncio.CancelledError(), BaseException("control exit")])
async def test_shutdown_control_flow_is_not_wrapped_as_business_error(settings, error):
    service = MonitorService(settings(exporter="none"))
    service._provider = SimpleNamespace(shutdown=Mock(side_effect=error))
    with pytest.raises(type(error)):
        await service.close()
    assert service._state == "close_failed" and service._pool is None


@pytest.mark.parametrize("enabled", [False, True])
def test_extra_attributes_require_opt_in_and_drops_are_counted(settings, enabled):
    service = MonitorService(settings(attribute_keys=["messaging.topic"] if enabled else []))
    attributes = service.policy.attributes({"messaging.topic": "topic"})
    assert attributes == ({"messaging.topic": "topic"} if enabled else {})
    assert service.diagnostics.snapshot().get("attributes_dropped", 0) == int(not enabled)


@pytest.mark.parametrize("decorator", [AutoTrace("typo"), BizTrace(id_expr="typo.value")])
def test_unknown_business_expression_root_fails_when_decorated(decorator):
    with pytest.raises(ValueError, match="未声明的参数"):
        decorator(lambda identifier: identifier)


@pytest.mark.parametrize("expression", ["'literal'", "True", "None", "42", "identifier.value"])
def test_literal_and_declared_business_expression_roots_are_allowed(expression):
    def function(identifier):
        return identifier

    assert callable(AutoTrace(expression)(function))
    assert callable(BizTrace(id_expr=expression)(function))


async def test_close_drops_live_spans_after_admission_stops(settings):
    service = MonitorService(settings())
    exporter = InMemorySpanExporter()
    await service.open(diagnostic_logger=logger, exporter=exporter)
    with service.span("unfinished"):
        await service.close()
    assert service.get_statistics()["dropped_spans"] == 1
    assert exporter.get_finished_spans() == ()


async def test_exporter_is_closed_when_processor_construction_fails(settings, monkeypatch):
    service = MonitorService(settings())
    exporter = InMemorySpanExporter()
    shutdown = Mock(wraps=exporter.shutdown)
    monkeypatch.setattr(exporter, "shutdown", shutdown)
    monkeypatch.setattr(
        MonitorSpanProcessor, "__init__", Mock(side_effect=RuntimeError("processor"))
    )
    with pytest.raises(MonitorException):
        await service.open(diagnostic_logger=logger, exporter=exporter)
    assert service._exporter is exporter and service._processor is None
    await service.close()
    shutdown.assert_called_once_with()


@pytest.mark.parametrize("limit", [64, 65, 66])
@pytest.mark.parametrize("with_baggage", [False, True])
def test_injection_respects_budget_smaller_than_traceparent(settings, limit, with_baggage):
    service = MonitorService(
        settings(
            max_propagation_bytes=limit,
            propagators=["tracecontext", "baggage"] if with_baggage else ["tracecontext"],
            baggage_keys=["region"] if with_baggage else [],
        )
    )
    parent = trace.set_span_in_context(
        trace.NonRecordingSpan(trace.SpanContext(123, 456, True, trace.TraceFlags(1))),
        context.Context(),
    )
    if with_baggage:
        parent = baggage.set_baggage("region", "west", parent)
    headers = {"x-caller": "kept", "traceparent": "old", "baggage": "old", "tracestate": "old"}
    with service.bind(parent):
        result = service.inject(headers)
    assert result["x-caller"] == "kept"
    assert "baggage" not in result and "tracestate" not in result
    assert ("traceparent" in result) is (limit == 66)
    assert (
        sum(
            len(key.encode()) + len(value.encode())
            for key, value in result.items()
            if key != "x-caller"
        )
        <= limit
    )
    assert service.diagnostics.snapshot().get("propagation_dropped", 0) == int(
        limit < 66 or with_baggage
    )
    assert headers == {
        "x-caller": "kept",
        "traceparent": "old",
        "baggage": "old",
        "tracestate": "old",
    }
