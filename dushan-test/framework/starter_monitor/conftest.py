from concurrent.futures import ThreadPoolExecutor
from contextlib import AsyncExitStack
from threading import Lock

import grpc
import pytest
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2, trace_service_pb2_grpc
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from fixtures.config_factory import ConfigFactory
from fixtures.public_web_app import create_public_app
from framework.starter_monitor.config.monitor_settings import MonitorSettings
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_web.routing.router_registration import RouterRegistration


@pytest.fixture
def settings():
    def build(**overrides):
        values = ConfigFactory.values()["config"]["models"]["monitor"]
        values.update(
            service_name="monitor-test", service_version="test", enabled=True, sampler="always_on"
        )
        ConfigFactory.merge(values, overrides)
        return MonitorSettings.model_validate(values)

    return build


@pytest.fixture
def memory_exporters(monkeypatch):
    values = []

    def create(monitor):
        exporter = InMemorySpanExporter()
        values.append(exporter)
        return exporter

    monkeypatch.setattr(MonitorService, "_create_exporter", create)
    return values


@pytest.fixture
async def monitor_app(config_dir):
    async with AsyncExitStack() as stack:

        async def build(*, app_overrides=None, routers=(), **overrides):
            values = {
                "banner": {"enabled": False},
                "config": {
                    "models": {"monitor": {"enabled": True, "sampler": "always_on", **overrides}}
                },
            }
            ConfigFactory.merge(values, app_overrides or {})
            from fixtures.starter_steps import StarterSteps

            app = create_public_app(
                steps=StarterSteps.without_tenant(),
                base_dir=config_dir(values),
                environ={},
                routers=[RouterRegistration(router) for router in routers],
            )
            await stack.enter_async_context(app.router.lifespan_context(app))
            return app

        yield build


class Receiver(trace_service_pb2_grpc.TraceServiceServicer):
    def __init__(self, directory):
        self.directory = directory
        self.requests = []
        self.lock = Lock()
        self.status = None
        self.delay = 0

    def Export(self, request, context):
        import time

        if self.delay:
            deadline = time.monotonic() + self.delay
            while context.is_active() and time.monotonic() < deadline:
                time.sleep(0.01)
        if self.status is not None:
            context.abort(self.status, "opaque-sensitive-rpc-ticket")
        with self.lock:
            self.requests.append(request)
            (self.directory / f"batch-{len(self.requests)}.pb").write_bytes(
                request.SerializeToString()
            )
        return trace_service_pb2.ExportTraceServiceResponse()


@pytest.fixture
def receiver(tmp_path):
    service = Receiver(tmp_path)
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="monitor-test-receiver")
    server = grpc.server(executor)
    trace_service_pb2_grpc.add_TraceServiceServicer_to_server(service, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    service.endpoint = f"http://127.0.0.1:{port}"
    try:
        yield service
    finally:
        server.stop(0).wait(3)
        executor.shutdown(wait=True)
