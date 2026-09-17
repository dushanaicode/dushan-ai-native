import asyncio

import pytest

from framework.starter_mq.backend.redis_backend import RedisBackend
from framework.starter_mq.core.mq_runtime import MQRuntime
from server.bootstrap.bootstrapper import BootstrapError


@pytest.mark.parametrize("failure", ["connection", "timeout", "cancel"])
async def test_consumer_activation_failure_propagates_and_releases_runtime(
    mq_case, monkeypatch, failure
):
    case = mq_case
    entered = asyncio.Event()
    original = OSError("consumer subscription failed")
    runtimes = []
    activate = MQRuntime.activate

    async def capture(runtime):
        runtimes.append(runtime)
        await activate(runtime)

    async def messages(backend, definition, prefetch):
        entered.set()
        if failure == "connection":
            raise original
        await asyncio.Event().wait()
        yield

    monkeypatch.setattr(MQRuntime, "activate", capture)
    monkeypatch.setattr(RedisBackend, "messages", messages)
    task = asyncio.create_task(
        case.peer(
            config={
                "models": {"mq": {"command_timeout_seconds": 0.1 if failure == "timeout" else 2.0}}
            }
        )
    )
    try:
        if failure == "cancel":
            async with asyncio.timeout(20):
                await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(BootstrapError) as error:
                await task
            if failure == "connection":
                assert error.value.__cause__ is original
            else:
                assert isinstance(error.value.__cause__, TimeoutError)
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert runtimes and runtimes[0].phase == "closed"
    assert all(actor.done() for actor in runtimes[0].actors.values())
    assert case.runtime.phase == "ready"
