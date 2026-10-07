from dataclasses import FrozenInstanceError, asdict
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.starter_logging.context.log_context import LogContext
from framework.starter_web.context.http_observation import HttpObservation
from framework.starter_web.exception.error_log_recorder import ErrorLogRecorder

pytestmark = pytest.mark.unit


async def test_error_record_normalizes_request_diagnostics_before_crossing_spi():
    """提供者只收到安全事实，身份来自观察快照，路由不含实际请求参数。"""
    writer = AsyncMock()
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/items/private-path",
            "query_string": b"token=private-query",
            "headers": [(b"user-agent", b"token=private-agent " + b"a" * 300)],
            "state": {
                "web_route_template": "/items/{item_id}",
                HttpObservation.KEY: HttpObservation(
                    log_context=LogContext(account_id="42", tenant_id="8")
                ),
            },
        }
    )
    token = LogContext.begin_request("request-42")
    try:
        LogContext.bind_trace("trace-42", None)
        LogContext.set_client_ip("192.0.2.42")
        try:
            raise ValueError("password=private-error")
        except ValueError as error:
            await ErrorLogRecorder(writer).record(
                request, error, GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR, "token=private-msg"
            )
        assert LogContext.current().account_id is None
    finally:
        LogContext.reset(token)

    (record,) = writer.await_args.args
    assert record.trace_id == "trace-42"
    assert (record.account_id, record.tenant_id) == ("42", "8")
    assert (record.method, record.route) == ("POST", "/items/{item_id}")
    assert record.client_ip == "192.0.2.42"
    assert record.user_agent == "token=*** " + "a" * 190
    assert record.exception_name == "ValueError"
    assert record.exception_class_name == "builtins"
    assert record.exception_file_name.endswith("test_error_log_recorder.py")
    assert (
        record.exception_method_name
        == "test_error_record_normalizes_request_diagnostics_before_crossing_spi"
    )
    assert record.exception_line_number > 0
    assert record.exception_message == "token=***"
    assert record.result_code == 500
    assert "ValueError: password=***" in record.exception_stack_trace
    serialized = repr(asdict(record))
    for secret in (
        "private-path",
        "private-query",
        "private-agent",
        "private-error",
        "private-msg",
    ):
        assert secret not in serialized
    with pytest.raises(FrozenInstanceError):
        record.account_id = "other"


async def test_sensitive_error_projection_never_exposes_original_object_or_trace():
    """敏感异常先做安全快照，框架不向提供者交出原异常或堆栈引用。"""

    class SensitiveError(Exception):
        def __safe_diagnostic__(self):
            """模拟驱动异常提供的安全诊断副本。"""
            return RuntimeError("已脱敏的诊断")

    writer = AsyncMock()
    request = Request({"type": "http", "method": "GET", "path": "/failure", "headers": []})
    token = LogContext.begin_request("request-fallback")
    try:
        try:
            raise SensitiveError("opaque-private-driver")
        except SensitiveError as error:
            await ErrorLogRecorder(writer).record(
                request, error, GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR, "系统异常"
            )
    finally:
        LogContext.reset(token)

    (record,) = writer.await_args.args
    assert record.trace_id == "request-fallback"
    assert record.account_id is record.tenant_id is None
    assert record.client_ip == record.user_agent == ""
    assert record.exception_name == "RuntimeError"
    assert record.exception_stack_trace == "RuntimeError: 已脱敏的诊断\n"
    assert record.exception_file_name == record.exception_method_name == ""
    assert record.exception_line_number == 0
    assert "opaque-private-driver" not in repr(asdict(record))
