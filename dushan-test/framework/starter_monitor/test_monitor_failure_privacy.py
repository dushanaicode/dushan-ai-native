import asyncio

import pytest
from loguru import logger
from opentelemetry import context
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.core.sdk_log_guard import SdkLogGuard
from framework.starter_monitor.decorators.biz_trace import BizTrace
from framework.starter_monitor.exception.monitor_exception import MonitorException
from framework.starter_monitor.util.trace_utils import TraceUtils


class CloseOnceExporter(SpanExporter):
    def __init__(self):
        self.calls = 0

    def export(self, spans):
        return SpanExportResult.SUCCESS

    def shutdown(self):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("opaque-close-secret")


async def test_failed_shutdown_keeps_retryable_ownership(settings):
    service = MonitorService(settings())
    exporter = CloseOnceExporter()
    before = SdkLogGuard._users
    await service.open(diagnostic_logger=logger, exporter=exporter)
    with pytest.raises(MonitorException):
        await service.close()
    assert service.get_statistics()["state"] == "close_failed"
    await service.close()
    await service.close()
    assert exporter.calls == 2
    assert service.get_statistics()["state"] == "closed"
    assert service._pool is None and SdkLogGuard._users == before


async def test_startup_failure_rolls_back_sdk_worker_and_does_not_publish(monitor_app, monkeypatch):
    before = SdkLogGuard._users
    instances = []
    original = MonitorService._create_exporter

    def fail(service):
        instances.append(service)
        raise RuntimeError("opaque-initialization-secret")

    monkeypatch.setattr(MonitorService, "_create_exporter", fail)
    with pytest.raises(Exception, match="追踪资源"):
        await monitor_app()
    assert instances[0].get_statistics()["state"] == "closed"
    assert instances[0]._pool is None
    assert SdkLogGuard._users == before
    monkeypatch.setattr(MonitorService, "_create_exporter", original)


async def test_attributes_and_exception_events_never_serialize_objects(settings):
    service = MonitorService(
        settings(
            max_attribute_length=32,
            max_attributes=3,
            max_events=2,
            capture_business_ids=True,
            attribute_keys=["safe.label"],
        )
    )
    exporter = InMemorySpanExporter()
    await service.open(diagnostic_logger=logger, exporter=exporter)
    secret = "opaque-ticket-cookie-private-value"

    class Object:
        def __str__(self):
            pytest.fail("不得序列化任意对象")

    try:
        with service.bind():
            with service.span(
                "safe",
                {
                    "password": secret,
                    "safe.label": "x" * 100,
                    "cookie": secret,
                    "db.statement": secret,
                },
            ) as span:
                span.set_attribute("safe.label", Object())
                span.set_attribute("not.allowed", secret)
                span.record_exception(ValueError(secret))
                span.add_event(
                    "exception", {"exception.message": secret, "exception.stacktrace": secret}
                )
                span.add_event("extra", {"exception.message": secret})
                assert TraceUtils.get_current_trace_id() is not None
            with service.span("explicit") as explicit:
                TraceUtils.on_error(RuntimeError(secret), explicit)
        await service.flush()
        spans = exporter.get_finished_spans()
        assert spans[0].attributes["safe.label"] == "x" * 32
        assert len(spans[0].events) == 2
        assert spans[1].events[0].attributes["exception.type"] == "RuntimeError"
        assert secret not in "".join(span.to_json() for span in spans)
    finally:
        await service.close()


async def test_explicit_sensitive_business_field_is_not_collected(settings):
    service = MonitorService(settings(capture_business_ids=True))
    exporter = InMemorySpanExporter()
    await service.open(diagnostic_logger=logger, exporter=exporter)

    @BizTrace(id_expr="token")
    def work(token):
        return token

    try:
        with service.bind():
            assert work("opaque-sensitive") == "opaque-sensitive"
        await service.flush()
        assert "biz.id" not in exporter.get_finished_spans()[0].attributes
    finally:
        await service.close()


async def test_flush_cancellation_and_concurrent_shutdown_are_bounded(settings, receiver):
    receiver.delay = 2
    service = MonitorService(
        settings(
            endpoint=receiver.endpoint,
            export_timeout_seconds=0.1,
            flush_timeout_seconds=0.3,
            shutdown_timeout_seconds=0.3,
            max_queue_size=8,
            max_batch_size=1,
        )
    )
    await service.open(diagnostic_logger=logger)
    for _ in range(8):
        with service.span("queued"):
            pass
    flush = asyncio.create_task(service.flush())
    await asyncio.sleep(0.02)
    flush.cancel()
    with pytest.raises(asyncio.CancelledError):
        await flush
    before = asyncio.get_running_loop().time()
    await service.close()
    assert asyncio.get_running_loop().time() - before < 0.8
    assert service.get_statistics()["pending_spans"] == 0


async def test_closing_live_observation_does_not_cancel_business(settings):
    service = MonitorService(settings())
    exporter = InMemorySpanExporter()
    await service.open(diagnostic_logger=logger, exporter=exporter)
    original = context.get_current()
    with service.span("still-working"):
        await service.close()
        value = 42
    assert value == 42 and context.get_current() is original
    assert service.get_statistics()["active_spans"] == 0


async def test_exporter_work_cannot_trace_itself(settings):
    service = MonitorService(settings())

    class Exporter(SpanExporter):
        def export(self, spans):
            with service.span("exporter-recursion") as span:
                assert not span.is_recording()
            return SpanExportResult.SUCCESS

        def shutdown(self):
            pass

    await service.open(diagnostic_logger=logger, exporter=Exporter())
    try:
        with service.span("business"):
            pass
        assert await service.flush()
        assert service.get_statistics()["started_spans"] == 1
    finally:
        await service.close()


async def test_later_resource_startup_failure_closes_active_monitor(
    monitor_app, memory_exporters, monkeypatch, tmp_path
):
    from framework.starter_database.starter.database_starter import DatabaseStarter

    instances = []
    original = MonitorService.open

    async def open_monitor(service, **kwargs):
        await original(service, **kwargs)
        instances.append(service)

    async def fail_database(starter):
        raise RuntimeError("private-later-resource")

    monkeypatch.setattr(MonitorService, "open", open_monitor)
    monkeypatch.setattr(DatabaseStarter, "open", fail_database)
    with pytest.raises(Exception, match="数据库资源"):
        await monitor_app(
            app_overrides={
                "config": {
                    "models": {
                        "database": {
                            "enabled": True,
                            "sources": [
                                {
                                    "name": "primary",
                                    "url": f"sqlite+aiosqlite:///{(tmp_path / 'unused.sqlite').as_posix()}",
                                    "role": "primary",
                                    "weight": 100,
                                    "pool": None,
                                    "tls": None,
                                }
                            ],
                        }
                    }
                }
            }
        )
    assert len(memory_exporters) == 1
    assert instances[0].get_statistics()["state"] == "closed"
    assert instances[0]._pool is None and not instances[0]._guard_owned


async def test_exception_recording_failure_cannot_replace_business_exception(settings, monkeypatch):
    from framework.starter_monitor.core.monitor_span import MonitorSpan

    service = MonitorService(settings())
    await service.open(diagnostic_logger=logger, exporter=InMemorySpanExporter())
    error = ValueError("private-business-error")

    def broken(*args, **kwargs):
        raise RuntimeError("private-observer-error")

    monkeypatch.setattr(MonitorSpan, "record_exception", broken)
    try:
        with pytest.raises(ValueError) as received:
            with service.span("error"):
                raise error
        assert received.value is error
        assert service.get_statistics()["observation_failures"] == 1
    finally:
        await service.close()
