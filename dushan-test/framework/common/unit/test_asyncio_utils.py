import asyncio
from contextvars import Context, ContextVar

import anyio
import pytest
from loguru import logger

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils

pytestmark = pytest.mark.unit


async def test_bounded_gather_preserves_order_and_cancels_peers_on_failure():
    running = maximum = 0

    async def work(value):
        nonlocal running, maximum
        running += 1
        maximum = max(running, maximum)
        await asyncio.sleep(0)
        running -= 1
        return value

    result = await AsyncioUtils.gather_with_concurrency(
        2, *(lambda value=value: work(value) for value in range(8))
    )
    assert result == list(range(8)) and maximum == 2
    with pytest.raises(ValueError):
        await AsyncioUtils.gather_with_concurrency(0)
    cleaned = asyncio.Event()
    started = asyncio.Event()

    async def peer():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    async def fail():
        await started.wait()
        raise ValueError("expected")

    with pytest.raises(ExceptionGroup):
        await AsyncioUtils.gather_with_concurrency(2, peer, fail)
    assert cleaned.is_set()


async def test_background_tasks_are_owned_and_closed():
    helper = AsyncioUtils()
    other = AsyncioUtils()
    started, closed = asyncio.Event(), asyncio.Event()

    async def background():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            closed.set()

    task = helper.run_async_task(background())
    await started.wait()
    await other.aclose()
    assert not task.done()
    await helper.aclose()
    assert task.cancelled() and closed.is_set()
    with pytest.raises(RuntimeError):
        helper.run_async_task(background())


async def test_explicit_context_isolation_uses_python_context_contract():
    variable = ContextVar("resource", default=None)
    variable.set("parent")

    async def read():
        return variable.get()

    assert await AsyncioUtils.create_task(read()) == "parent"
    assert await AsyncioUtils.create_task(read(), context=Context()) is None
    assert variable.get() == "parent"


async def test_background_failure_is_logged_after_redaction():
    messages = []
    sink = logger.add(lambda message: messages.append(str(message)))
    helper = AsyncioUtils()

    async def fail():
        raise ValueError("password=private-value")

    try:
        task = helper.run_async_task(fail())
        await asyncio.gather(task, return_exceptions=True)
        await helper.aclose()
    finally:
        logger.remove(sink)
    output = "".join(messages)
    assert "后台任务执行失败" in output and "private-value" not in output


async def test_shield_survives_anyio_scope_cancellation():
    finalized = []

    async def finalize():
        await anyio.sleep(0)
        finalized.append(True)

    with anyio.CancelScope() as scope:
        scope.cancel()
        try:
            await anyio.sleep(0)
        except asyncio.CancelledError:
            await AsyncioUtils.run_cancellation_shielded(finalize())
    assert finalized == [True]


@pytest.mark.parametrize("suppress", [False, True])
async def test_shield_finishes_after_repeated_cancellation(suppress):
    started, release = asyncio.Event(), asyncio.Event()
    finished = []

    async def finalize():
        started.set()
        await release.wait()
        finished.append(True)
        return 7

    task = asyncio.create_task(
        AsyncioUtils.run_cancellation_shielded(finalize(), propagate_cancellation=not suppress)
    )
    await started.wait()
    task.cancel("first")
    await asyncio.sleep(0)
    task.cancel("second")
    release.set()
    if suppress:
        assert await task == 7
    else:
        with pytest.raises(asyncio.CancelledError) as caught:
            await task
        assert caught.value.args == ("first",)
    assert finished == [True]


@pytest.mark.parametrize("cancel_caller", [False, True])
@pytest.mark.parametrize("self_cancel", [False, True])
async def test_shield_distinguishes_protected_failure_from_caller_cancellation(
    cancel_caller, self_cancel
):
    started, release = asyncio.Event(), asyncio.Event()
    failure = RuntimeError("cleanup failure")

    async def operation():
        started.set()
        await release.wait()
        if self_cancel:
            raise asyncio.CancelledError("protected")
        raise failure

    task = asyncio.create_task(AsyncioUtils.run_cancellation_shielded(operation()))
    await started.wait()
    if cancel_caller:
        task.cancel("caller")
    release.set()
    with pytest.raises(
        asyncio.CancelledError if cancel_caller or self_cancel else RuntimeError
    ) as caught:
        await task
    if cancel_caller:
        assert caught.value.args == ("caller",)
        assert isinstance(
            caught.value.__cause__, asyncio.CancelledError if self_cancel else RuntimeError
        )
    elif not self_cancel:
        assert caught.value is failure


async def test_cleanup_aggregation_keeps_original_error_objects():
    cleanup_error = ValueError("cleanup")
    primary = RuntimeError("primary")

    async def action():
        raise cleanup_error

    result, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(action, "close")
    assert result is cleanup_error and cancellation is None
    with pytest.raises(RuntimeError) as caught:
        CleanupUtils.raise_collected_cleanup_errors("close", [result], primary_error=primary)
    assert caught.value is primary
    assert caught.value.__cause__.exceptions == (cleanup_error,)
