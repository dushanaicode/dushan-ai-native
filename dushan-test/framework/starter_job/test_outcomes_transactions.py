import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from framework.starter_job.definitions.enums.job_trigger_kind import JobTriggerKind
from framework.starter_job.model.job_request import JobRequest

from .test_runtime import wait_state


async def test_transaction_rollback_does_not_publish_definition(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        with pytest.raises(RuntimeError):
            async with case.app.state.database.transaction():
                await case.service.save(case.definition())
                raise RuntimeError("rollback")
        assert await case.runtime.definitions.get_definition("job") is None
    assert not case.runtime.scheduler.get_jobs()


async def test_observation_failure_does_not_change_success(job_case):
    case = job_case
    case.probe.record_failure = True
    with case.app.state.application_context.execution():
        await case.service.save(case.definition())
        request = await case.service.trigger("job")
    await wait_state(case, request, "succeeded")
    assert case.runtime.observation_failures == 1


async def test_async_timeout_and_failure_stop_policy(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(parameters={"mode": "wait"}, timeout_seconds=0.03))
        request = await case.service.trigger("job")
    await wait_state(case, request, "timed_out")
    with case.app.state.application_context.execution():
        await case.service.save(
            case.definition(parameters={"mode": "fail"}, stop_after_failure=True)
        )
        request = await case.service.trigger("job")
    await wait_state(case, request, "failed")
    async with asyncio.timeout(3):
        while True:
            with case.app.state.application_context.execution():
                definition = await case.runtime.definitions.get_definition("job")
            if not definition.enabled:
                break
            await asyncio.sleep(0.01)


async def test_sync_thread_timeout_holds_resources_until_real_exit(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(handler_key="blocking", timeout_seconds=0.03))
        request = await case.service.trigger("job")
    async with asyncio.timeout(3):
        while not case.probe.thread_entered.is_set():
            await asyncio.sleep(0.005)
    assert case.runtime.invoker.running_threads == 1
    async with asyncio.timeout(3):
        while not case.runtime.invoker.timed_out_threads:
            await asyncio.sleep(0.005)
    closing = asyncio.create_task(case.runtime.close())
    await asyncio.sleep(0)
    assert not closing.done()
    closing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closing
    closing = asyncio.create_task(case.runtime.close())
    await asyncio.sleep(0)
    assert not closing.done()
    case.probe.thread_release.set()
    await asyncio.wait_for(closing, 3)
    assert case.runtime.invoker.running_threads == 0
    async with case.engine.connect() as connection:
        state = await connection.scalar(
            select(case.module.RequestRow.state).where(
                case.module.RequestRow.request_key == request
            )
        )
    assert state == "unknown"


async def test_misfire_grace_and_stale_snapshot_are_skipped(job_case):
    case = job_case
    definition = case.definition()
    now = datetime.now(UTC)
    with case.app.state.application_context.execution():
        await case.service.save(definition)
        old = JobRequest(
            request_id="old-occurrence",
            definition=definition,
            trigger=JobTriggerKind.SCHEDULED,
            scheduled_at=now - timedelta(seconds=120),
            ready_at=now,
            attempt=1,
        )
        await case.runtime.requests.submit(old, pending_limit=10)
    await wait_state(case, old.request_id, "skipped")
    assert not case.probe.runs
