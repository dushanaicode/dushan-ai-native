import asyncio
from dataclasses import FrozenInstanceError

import pytest

from framework.starter_logging.context.log_context import LogContext

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_log_context() -> None:
    """每个测试前后清空当前任务的日志上下文。"""
    LogContext.clear()
    yield
    LogContext.clear()


def test_log_context_restores_nested_trace_and_is_immutable() -> None:
    """嵌套追踪可恢复原值，当前日志上下文不可变。"""
    request_token = LogContext.begin_request("request-1")
    LogContext.set_client_ip("198.51.100.8")
    LogContext.set_tenant(7)
    LogContext.set_principal(11, 12, "tenant")
    trace_token = LogContext.bind_trace("trace-1", "span-1")
    try:
        current = LogContext.current()
        assert current.request_id == "request-1"
        assert current.trace_id == "trace-1"
        assert current.tenant_id == 7
        assert current.account_id == 11
        assert current.membership_id == 12
        assert current.realm == "tenant"
        with pytest.raises(FrozenInstanceError):
            current.tenant_id = 8  # type: ignore[misc]
    finally:
        LogContext.reset(trace_token)

    assert LogContext.current().trace_id is None
    assert LogContext.current().client_ip == "198.51.100.8"
    LogContext.reset(request_token)
    assert LogContext.current() == LogContext()


async def test_log_context_isolates_concurrent_tasks() -> None:
    """并发任务各自保存请求上下文，不污染调用者。"""
    first_ready = asyncio.Event()
    second_ready = asyncio.Event()

    async def read_context(
        request_id: str, ready: asyncio.Event, peer_ready: asyncio.Event
    ) -> LogContext:
        """等待另一个任务就绪后读取自身的上下文。"""
        token = LogContext.begin_request(request_id)
        try:
            ready.set()
            await peer_ready.wait()
            return LogContext.current()
        finally:
            LogContext.reset(token)

    first, second = await asyncio.gather(
        read_context("request-1", first_ready, second_ready),
        read_context("request-2", second_ready, first_ready),
    )

    assert first.request_id == "request-1"
    assert second.request_id == "request-2"
    assert LogContext.current() == LogContext()
