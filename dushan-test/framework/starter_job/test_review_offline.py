import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import framework.starter_job.core.job_runtime as runtime_module
from fixtures.config_factory import ConfigFactory
from framework.starter_job.config.job_settings import JobSettings
from framework.starter_job.core.job_invoker import JobInvoker
from framework.starter_job.core.job_runtime import JobRuntime
from framework.starter_job.core.tenant_job_runner import TenantJobRunner
from framework.starter_job.definitions.constants.job_error_codes import JobErrorCodes
from framework.starter_job.definitions.enums.job_state import JobState
from framework.starter_job.definitions.enums.job_trigger_kind import JobTriggerKind
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.model.job_outcome import JobOutcome


async def test_owner_acquire_failure_does_not_accept_requests(monkeypatch):
    settings = JobSettings.model_validate(
        {
            **ConfigFactory.values()["config"]["models"]["job"],
            "enabled": True,
            "owner_enabled": True,
        }
    )
    lease = SimpleNamespace(acquire=AsyncMock(side_effect=OSError("lease")), release_required=False)
    monkeypatch.setattr(runtime_module, "RedisLeaseLock", lambda *args, **kwargs: lease)
    runtime = JobRuntime(
        settings,
        object(),
        SimpleNamespace(timezone="UTC"),
        object(),
        object(),
        object(),
        object(),
        SimpleNamespace(get_client=lambda key: None, build_full_key=lambda *args: "lease"),
        None,
        None,
        None,
    )
    try:
        with pytest.raises(OSError):
            await runtime.open()
        assert not runtime.accepting
        with pytest.raises(JobException) as caught:
            await runtime.submit_manual("named-job")
        assert caught.value.error_code is JobErrorCodes.CLOSED
    finally:
        await runtime.close()


async def test_record_only_waits_for_record_before_propagating_cancel():
    entered, release, written = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def record(*args):
        entered.set()
        await release.wait()
        written.set()

    runtime = SimpleNamespace(invoker=SimpleNamespace(record=record), observation_failures=0)
    request = SimpleNamespace(definition=SimpleNamespace(tenant_id=None))
    task = asyncio.create_task(JobRuntime._record_only(runtime, request, object(), object()))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert written.is_set() and runtime.observation_failures == 0


async def test_lease_release_failure_still_shuts_down_scheduler():
    callbacks = []
    scheduler = SimpleNamespace(
        running=True,
        pause=Mock(),
        add_listener=lambda callback, event: callbacks.append(callback),
        shutdown=Mock(side_effect=lambda **kwargs: callbacks[0](None)),
    )
    runtime = SimpleNamespace(
        accepting=True,
        phase="running",
        owner=True,
        scheduler=scheduler,
        _stop=asyncio.Event(),
        _renew_stop=asyncio.Event(),
        _loop_task=None,
        _renew_task=None,
        running={},
        lease=SimpleNamespace(
            release_required=True, release=AsyncMock(side_effect=OSError("release"))
        ),
    )
    with pytest.raises(OSError, match="release"):
        await JobRuntime._close(runtime)
    scheduler.shutdown.assert_called_once_with(wait=False)
    assert runtime.phase == "closed" and not runtime.owner and not runtime.accepting


async def test_record_keeps_business_error_code_without_raw_message():
    records = SimpleNamespace(record=AsyncMock())
    invoker = JobInvoker(
        None,
        None,
        None,
        records,
        SimpleNamespace(result_max_length=1024, record_timeout_seconds=1),
        None,
    )
    request = SimpleNamespace(
        request_id="request",
        definition=SimpleNamespace(id="named-job", handler_key="handler"),
        attempt=1,
        trigger=JobTriggerKind.MANUAL,
    )
    await invoker.record(
        request,
        JobOutcome(
            JobState.FAILED, error=JobException(JobErrorCodes.CONFIGURATION, msg="private-marker")
        ),
        datetime.now(UTC),
        None,
    )
    summary = records.record.call_args.args[0].summary
    assert str(JobErrorCodes.CONFIGURATION.code) in summary and "JobException" in summary
    assert "private-marker" not in summary


@pytest.mark.parametrize(
    ("first_state", "second_state", "settlement_fails", "expected_state"),
    [
        (JobState.SUCCEEDED, JobState.SUCCEEDED, False, JobState.SUCCEEDED),
        (JobState.SKIPPED, JobState.SUCCEEDED, False, JobState.SUCCEEDED),
        (JobState.FAILED, JobState.FAILED, False, JobState.FAILED),
        (JobState.SUCCEEDED, JobState.TIMED_OUT, False, JobState.TIMED_OUT),
        (JobState.SUCCEEDED, JobState.UNKNOWN, False, JobState.UNKNOWN),
        (JobState.SUCCEEDED, JobState.CANCELLED, False, JobState.CANCELLED),
        (JobState.SUCCEEDED, JobState.SUCCEEDED, True, JobState.UNKNOWN),
        (JobState.SUCCEEDED, JobState.FAILED, True, JobState.UNKNOWN),
    ],
)
async def test_fanout_preserves_observation_errors(
    first_state, second_state, settlement_fails, expected_state
):
    async def target_batches():
        yield ("1",)
        yield ("2", "3")

    observation_errors = (OSError("record-1"), OSError("record-2"))
    states = (first_state, second_state)
    outcomes = [
        JobOutcome(
            state,
            result=f"result-{index}",
            error=None if state in {JobState.SUCCEEDED, JobState.SKIPPED} else ValueError("job"),
            observation_errors=(observation_errors[index],),
        )
        for index, state in enumerate(states)
    ]
    leases = [
        SimpleNamespace(
            request_id="request",
            tenant_id=tenant_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=1),
        )
        for tenant_id in ("1", "2")
    ]
    settlement_error = OSError("settlement")

    async def settle(lease):
        if settlement_fails and lease.tenant_id == "2":
            raise settlement_error

    targets = SimpleNamespace(
        claim=AsyncMock(side_effect=[*leases, None]),
        complete=AsyncMock(side_effect=settle),
        release=AsyncMock(side_effect=settle),
    )
    invoker = SimpleNamespace(
        settings=SimpleNamespace(command_timeout_seconds=1),
        invoke=AsyncMock(side_effect=outcomes),
    )
    runner = TenantJobRunner(
        SimpleNamespace(ready=True, target_batches=target_batches), targets, invoker, 60
    )
    result = await runner.run(SimpleNamespace(request_id="request"))

    assert result.state is expected_state
    assert result.observation_errors == observation_errors
    if settlement_fails:
        assert result.error is settlement_error
    elif expected_state is not JobState.SUCCEEDED:
        selected = outcomes[0] if first_state is JobState.FAILED else outcomes[1]
        assert result.error is selected.error and result.result == selected.result
    interrupted = expected_state in {JobState.UNKNOWN, JobState.CANCELLED}
    assert targets.claim.await_count == (2 if interrupted else 3)
    assert invoker.invoke.await_count == 2
