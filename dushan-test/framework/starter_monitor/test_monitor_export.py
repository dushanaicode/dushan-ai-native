import asyncio
import logging
import threading
from time import perf_counter

import grpc
import pytest
from loguru import logger
from opentelemetry.sdk.trace.export import SpanExporter

from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.core.sdk_log_guard import SdkLogGuard


@pytest.mark.parametrize("uppercase_scheme", [False, True])
async def test_real_sdk_otlp_export_to_local_receiver(settings, receiver, uppercase_scheme):
    endpoint = (
        receiver.endpoint.replace("http://", "HTTP://") if uppercase_scheme else receiver.endpoint
    )
    service = MonitorService(settings(endpoint=endpoint))
    await service.open(diagnostic_logger=logger)
    try:
        with service.span(
            "real-root", {"password": "opaque-secret", "http.url": "https://host/private-token"}
        ) as parent:
            with service.span("real-child", {"http.request.method": "POST"}):
                pass
        assert await service.flush()
        spans = [
            span
            for req in receiver.requests
            for resource in req.resource_spans
            for scope in resource.scope_spans
            for span in scope.spans
        ]
        assert len(spans) == 2
        child, root = spans
        assert child.parent_span_id == root.span_id
        assert root.trace_id == parent.get_span_context().trace_id.to_bytes(16, "big")
        assert b"opaque-secret" not in b"".join(
            req.SerializeToString() for req in receiver.requests
        )
    finally:
        await service.close()
    assert service.get_statistics()["pending_spans"] == 0


async def test_export_failure_is_bounded_and_rpc_details_are_not_logged(settings, receiver, caplog):
    receiver.status = grpc.StatusCode.PERMISSION_DENIED
    service = MonitorService(
        settings(
            endpoint=receiver.endpoint,
            export_timeout_seconds=0.1,
            flush_timeout_seconds=0.3,
            shutdown_timeout_seconds=0.3,
        )
    )
    await service.open(diagnostic_logger=logger)
    try:
        with caplog.at_level(logging.DEBUG), service.span("rejected"):
            pass
        start = perf_counter()
        assert await service.flush() is False
        assert perf_counter() - start < 1
        assert "opaque-sensitive-rpc-ticket" not in caplog.text
        assert service.get_statistics()["export_failures"] == 1
    finally:
        await service.close()


async def test_queue_pressure_shutdown_budget_and_thread_release(settings, receiver):
    receiver.delay = 2
    before = {thread.ident for thread in threading.enumerate()}
    service = MonitorService(
        settings(
            endpoint=receiver.endpoint,
            max_queue_size=6,
            max_batch_size=1,
            schedule_delay_millis=1,
            export_timeout_seconds=0.1,
            flush_timeout_seconds=0.3,
            shutdown_timeout_seconds=0.3,
        )
    )
    await service.open(diagnostic_logger=logger)
    for index in range(40):
        with service.span(f"operation-{index}"):
            pass
    assert service.get_statistics()["dropped_spans"] >= 34
    start = perf_counter()
    close = asyncio.create_task(service.close())
    await asyncio.sleep(0)
    close.cancel()
    with pytest.raises(asyncio.CancelledError):
        await close
    await service.close()
    assert perf_counter() - start < 1
    assert service.get_statistics()["pending_spans"] == 0
    assert service.get_statistics()["budget_dropped_spans"] > 0
    assert not [
        thread
        for thread in threading.enumerate()
        if thread.ident not in before
        and (thread.name.startswith("monitor-lifecycle") or thread.name.startswith("OtelBatch"))
    ]


async def test_sdk_log_filter_is_shared_only_for_protection(settings):
    a, b = MonitorService(settings(exporter="none")), MonitorService(settings(exporter="none"))
    before = SdkLogGuard._users
    await a.open(diagnostic_logger=logger)
    await b.open(diagnostic_logger=logger)
    assert SdkLogGuard._users == before + 2
    await a.close()
    assert SdkLogGuard._users == before + 1
    await b.close()
    assert SdkLogGuard._users == before


class FailingExporter(SpanExporter):
    def export(self, spans):
        raise RuntimeError("private-export-data")

    def shutdown(self):
        pass


async def test_exporter_exception_does_not_change_business_result(settings):
    service = MonitorService(settings())
    await service.open(diagnostic_logger=logger, exporter=FailingExporter())
    with service.span("business"):
        result = 42
    assert await service.flush() is False
    assert result == 42
    await service.close()
