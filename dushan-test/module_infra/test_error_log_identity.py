from asyncio import CancelledError
from contextlib import asynccontextmanager, nullcontext
from functools import partial
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.background import BackgroundTask
from starlette.responses import PlainTextResponse, StreamingResponse

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.starter_logging.context.log_context import LogContext
from framework.starter_web.context.http_observation import HttpObservation
from framework.starter_web.exception.error_log_recorder import ErrorLogRecorder
from framework.starter_web.exception.global_exception_handler import GlobalExceptionHandler
from framework.starter_web.middleware.access_log_middleware import AccessLogMiddleware
from framework.starter_web.middleware.request_context_middleware import RequestContextMiddleware
from framework.starter_web.middleware.web_exception_middleware import WebExceptionMiddleware
from framework.starter_web.routing.web_route import WebRoute
from module_infra.service.logger.api_error_log_service_impl import ApiErrorLogServiceImpl
from module_infra.spi.logger.api_access_log_service_provider_adapter import (
    ApiAccessLogServiceProviderAdapter,
)
from module_infra.spi.logger.api_error_log_service_provider_adapter import (
    ApiErrorLogServiceProviderAdapter,
)


@pytest.mark.parametrize("account_id", ["42", None])
@pytest.mark.parametrize("failure_phase", ["endpoint", "stream", "background"])
async def test_error_log_keeps_request_identity_after_guard_exits(account_id, failure_phase):
    error_rows = []
    access_rows = []
    guard_exited = []
    write_tenants = []

    @asynccontextmanager
    async def guard(request):
        token = LogContext.bind_principal(
            account_id, "8" if account_id is not None else None, None, "tenant"
        )
        try:
            yield
        finally:
            LogContext.reset(token)
            guard_exited.append(True)

    @asynccontextmanager
    async def workload_scope(code, tenant_id):
        assert code == "infra.log.write"
        write_tenants.append(tenant_id)
        yield

    async def run_isolated(writer, *args):
        await writer(*args)

    async def insert(row):
        assert len(guard_exited) == 2
        error_rows.append(row)

    service = ApiErrorLogServiceImpl()
    service.api_error_log_mapper = SimpleNamespace(insert=AsyncMock(side_effect=insert))
    service.tenant_settings = SimpleNamespace(default_tenant_id="1")
    service.workloads = SimpleNamespace(scope=workload_scope)
    service.database = SimpleNamespace(scope=nullcontext)
    adapter = ApiErrorLogServiceProviderAdapter()
    adapter.service = service
    adapter.settings = SimpleNamespace(application_id="identity-test")
    adapter.tasks = SimpleNamespace(run_isolated=run_isolated)
    handler = GlobalExceptionHandler(error_recorder=ErrorLogRecorder(adapter.write))

    access_adapter = ApiAccessLogServiceProviderAdapter()
    access_adapter.service = SimpleNamespace(
        create_api_access_log=AsyncMock(side_effect=access_rows.append)
    )
    access_adapter.settings = adapter.settings
    app = FastAPI()
    app.router.route_class = partial(WebRoute, access_guard=guard)
    app.state.web_logging_owner = "identity-test"
    app.state.web_trusted_proxies = ()
    app.state.access_log_provider = access_adapter
    app.state.access_log_tasks = SimpleNamespace(run_isolated=run_isolated)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(WebExceptionMiddleware, handler=handler, owner="identity-test")
    app.add_middleware(RequestContextMiddleware, access_log_enabled=False)
    handler.register(app)

    async def fail():
        raise RuntimeError("request failed")

    @app.get("/failure")
    async def failure():
        if failure_phase == "endpoint":
            await fail()
        if failure_phase == "background":
            return PlainTextResponse("ok", background=BackgroundTask(fail))

        async def chunks():
            yield b"first"
            await fail()

        return StreamingResponse(chunks())

    @app.get("/success")
    async def success():
        return {"ok": True}

    previous_context = LogContext.current()
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        assert (await client.get("/success")).status_code == 200
        response = await client.get("/failure")

    if failure_phase == "endpoint":
        assert response.json()["code"] == 500
    assert len(error_rows) == 1
    row = error_rows[0]
    expected_identity = (42, 2) if account_id is not None else (None, 0)
    assert (row.user_id, row.user_type) == expected_identity
    assert (access_rows[0].user_id, access_rows[0].user_type) == expected_identity
    assert write_tenants == ["8" if account_id is not None else "1"]
    assert row.request_url == "/failure"
    assert row.application_name == "identity-test"
    assert access_rows[0].application_name == row.application_name
    assert LogContext.current() == previous_context


@pytest.mark.parametrize("failure_type", [RuntimeError, CancelledError])
async def test_error_log_writer_failure_restores_log_identity(failure_type):
    snapshot = LogContext(account_id="42", tenant_id="8", realm="tenant")
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/failure",
            "headers": [],
            "state": {HttpObservation.KEY: HttpObservation(log_context=snapshot)},
        }
    )
    previous_context = LogContext.current()

    async def write(record):
        assert LogContext.current().account_id == "42"
        assert LogContext.current().tenant_id == "8"
        assert record.account_id == "42"
        assert record.tenant_id == "8"
        raise failure_type("write interrupted")

    expected = pytest.raises(CancelledError) if failure_type is CancelledError else nullcontext()
    with expected:
        await ErrorLogRecorder(write).record(
            request,
            RuntimeError("original"),
            GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR,
            "异常",
        )

    assert LogContext.current() == previous_context
