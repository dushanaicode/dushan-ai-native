from dataclasses import asdict
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import HTTPConnection

from framework.starter_logging.context.log_context import LogContext
from framework.starter_web.context.http_observation import HttpObservation
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.middleware import access_log_middleware, request_context_middleware
from framework.starter_web.middleware.access_log_middleware import AccessLogMiddleware
from framework.starter_web.middleware.request_context_middleware import RequestContextMiddleware
from framework.starter_web.routing.access_log_policy import AccessLogPolicy
from framework.starter_web.routing.operate_type_enum import OperateTypeEnum


@pytest.fixture
def logged_request():
    provider = SimpleNamespace(write=AsyncMock())

    async def run_isolated(writer, record):
        await writer(record)

    tasks = SimpleNamespace(run_isolated=AsyncMock(side_effect=run_isolated))

    async def endpoint(scope, receive, send):
        token = LogContext.begin_request("request-id")
        try:
            LogContext.bind_trace("trace-id", "span-id")
            LogContext.set_principal("42", None, "admin")
            LogContext.set_tenant(8)
            LogContext.set_client_ip("192.0.2.10")
            await send({"type": "http.response.start", "status": 201, "headers": []})
            await send({"type": "http.response.body", "body": b"first", "more_body": True})
            await send({"type": "http.response.body", "body": b"last", "more_body": False})
        finally:
            LogContext.reset(token)

    scope = {
        "type": "http",
        "app": SimpleNamespace(
            state=SimpleNamespace(access_log_provider=provider, access_log_tasks=tasks)
        ),
        "endpoint": endpoint,
        "method": "POST",
        "path": "/items/path-secret",
        "headers": [(b"user-agent", b"token=agent-secret " + b"a" * 300)],
        "state": {"web_route_template": "/items/{item_id}"},
    }
    with RequestContext.bind(HTTPConnection(scope), "request-id", "192.0.2.10"):
        yield SimpleNamespace(
            scope=scope,
            receive=AsyncMock(),
            send=AsyncMock(),
            provider=provider,
            tasks=tasks,
            endpoint=endpoint,
            middleware=AccessLogMiddleware(endpoint),
        )


@pytest.fixture
def request_log_pair(logged_request, monkeypatch):
    request = logged_request
    request.scope["scheme"] = "http"
    request.scope["app"].state.web_trusted_proxies = ()
    request.scope["app"].state.web_logging_owner = "operation-type-test"
    request.middleware = RequestContextMiddleware(request.middleware, access_log_enabled=True)
    request.log_info = Mock()
    monkeypatch.setattr(request_context_middleware.logger, "info", request.log_info)
    return request


@pytest.mark.parametrize("policy", [None, AccessLogPolicy(enabled=True)])
@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("GET", 1),
        ("POST", 2),
        ("PUT", 3),
        ("PATCH", 3),
        ("DELETE", 4),
        ("HEAD", 0),
        ("OPTIONS", 0),
        ("TRACE", 0),
        ("CONNECT", 0),
        ("REPORT", 0),
    ],
)
async def test_default_operation_type_matches_in_both_logs(
    request_log_pair, policy, method, expected
):
    request = request_log_pair
    request.scope["method"] = method
    if policy is not None:
        policy(request.endpoint)

    await request.middleware(request.scope, request.receive, request.send)

    request.provider.write.assert_awaited_once()
    request.log_info.assert_called_once()
    assert request.provider.write.await_args.args[0].operate_type == expected
    assert request.log_info.call_args.args[-1] == expected


@pytest.mark.parametrize(
    ("operate_type", "expected"),
    [(OperateTypeEnum.OTHER, 0), (OperateTypeEnum.EXPORT, 5), (OperateTypeEnum.IMPORT, 6)],
)
async def test_explicit_operation_type_overrides_method_in_both_logs(
    request_log_pair, operate_type, expected
):
    request = request_log_pair
    AccessLogPolicy(enabled=True, operate_type=operate_type)(request.endpoint)

    await request.middleware(request.scope, request.receive, request.send)

    assert request.provider.write.await_args.args[0].operate_type == expected
    assert request.log_info.call_args.args[-1] == expected


async def test_no_provider_passes_through_without_observation(monkeypatch):
    app, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
    tasks = SimpleNamespace(run_isolated=AsyncMock())
    scope = {
        "type": "http",
        "app": SimpleNamespace(
            state=SimpleNamespace(access_log_provider=None, access_log_tasks=tasks)
        ),
    }
    timer = Mock(side_effect=AssertionError("未绑定时不应记录计时"))
    monkeypatch.setattr(access_log_middleware, "perf_counter", timer)

    await AccessLogMiddleware(app)(scope, receive, send)

    app.assert_awaited_once_with(scope, receive, send)
    tasks.run_isolated.assert_not_awaited()
    timer.assert_not_called()


@pytest.mark.parametrize("business_code", [None, 0, 604])
async def test_provider_writes_one_record_per_request(logged_request, monkeypatch, business_code):
    request = logged_request
    AccessLogPolicy(
        enabled=True,
        operate_module="items",
        operate_name="新增条目",
        operate_type=OperateTypeEnum.CREATE,
    )(request.endpoint)
    request.scope["state"][HttpObservation.KEY] = HttpObservation(business_code=business_code)
    ticks = iter([1.0, 1.125, 2.0, 2.25])
    monkeypatch.setattr(access_log_middleware, "perf_counter", lambda: next(ticks))
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    context = LogContext.current()

    await request.middleware(request.scope, request.receive, request.send)
    await request.middleware(request.scope, request.receive, request.send)

    after = datetime.now(timezone.utc).replace(tzinfo=None)
    assert request.provider.write.await_count == request.tasks.run_isolated.await_count == 2
    assert request.send.await_count == 6
    assert LogContext.current() == context
    for index, call in enumerate(request.provider.write.await_args_list):
        record = call.args[0]
        request.tasks.run_isolated.assert_any_await(request.provider.write, record)
        assert before <= record.begin_time <= record.end_time <= after
        assert asdict(record) == {
            "trace_id": "trace-id",
            "account_id": "42",
            "tenant_id": 8,
            "method": "POST",
            "route": "/items/{item_id}",
            "client_ip": "192.0.2.10",
            "user_agent": "token=*** " + "a" * 190,
            "operate_module": "items",
            "operate_name": "新增条目",
            "operate_type": 2,
            "begin_time": record.begin_time,
            "end_time": record.end_time,
            "duration_ms": [125, 250][index],
            "result_code": 201 if business_code is None else business_code,
        }


async def test_disabled_policy_does_not_write(logged_request):
    request = logged_request
    AccessLogPolicy(enabled=False)(request.endpoint)

    await request.middleware(request.scope, request.receive, request.send)

    assert request.send.await_count == 3
    request.tasks.run_isolated.assert_not_awaited()
    request.provider.write.assert_not_awaited()


@pytest.mark.parametrize("scope_type", ["websocket", "lifespan"])
async def test_non_http_passes_through(scope_type):
    app, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
    scope = {"type": scope_type}

    await AccessLogMiddleware(app)(scope, receive, send)

    app.assert_awaited_once_with(scope, receive, send)


async def test_provider_failure_logs_only_exception_type(logged_request, monkeypatch):
    request = logged_request
    request.provider.write.side_effect = RuntimeError("private-error-detail")
    log_error = Mock()
    monkeypatch.setattr(access_log_middleware.logger, "error", log_error)

    await request.middleware(request.scope, request.receive, request.send)

    assert request.send.await_count == 3
    assert request.provider.write.await_count == request.tasks.run_isolated.await_count == 1
    log_error.assert_called_once_with("访问日志写入失败: {}", "RuntimeError")


@pytest.mark.parametrize("client_ip", [None, "2001:db8::1"])
async def test_access_metadata_uses_request_context_contract(logged_request, client_ip):
    """访问日志使用可信请求地址与首个 UA，保留缺失值和脱敏限制。"""
    request = logged_request
    request.scope["headers"] = [
        (b"user-agent", b"token=private-agent"),
        (b"user-agent", b"ignored-duplicate-agent"),
        (b"x-forwarded-for", b"203.0.113.99"),
    ]
    with RequestContext.bind(HTTPConnection(request.scope), "request-id", client_ip):
        await request.middleware(request.scope, request.receive, request.send)

    (record,) = request.provider.write.await_args.args
    assert record.client_ip == ("" if client_ip is None else client_ip)
    assert record.user_agent == "token=***"


async def test_downstream_exception_propagates_without_writing(logged_request):
    request = logged_request
    app = AsyncMock(side_effect=RuntimeError("downstream-failed"))

    with pytest.raises(RuntimeError, match="downstream-failed"):
        await AccessLogMiddleware(app)(request.scope, request.receive, request.send)

    request.tasks.run_isolated.assert_not_awaited()
    request.provider.write.assert_not_awaited()
