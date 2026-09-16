import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from framework.starter_job.core.job_service import JobService
from framework.starter_job.enums.job_trigger_kind import JobTriggerKind
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.model.job_request import JobRequest
from server.starter_server import create_app

from .test_runtime import wait_state


async def test_two_applications_have_one_owner_and_shared_manual_queue(job_case):
    case = job_case
    other = create_app(base_dir=case.config_path, environ={})
    async with other.router.lifespan_context(other):
        assert case.runtime.owner and not other.state.job.owner
        with case.app.state.application_context.execution():
            await case.service.save(case.definition())
        with other.state.application_context.execution():
            service = other.state.application_context.container.get(JobService)
            request = await service.trigger("job")
        await wait_state(case, request, "succeeded")
        assert case.probe.runs == [(request, 1)]
        with other.state.application_context.execution():
            assert not other.state.application_context.container.get(case.module.Probe).runs


async def test_manual_and_scheduled_requests_share_instance_limit(job_case):
    case = job_case
    definition = case.definition(parameters={"mode": "wait"})
    with case.app.state.application_context.execution():
        await case.service.save(definition)
        first = await case.service.trigger("job")
    await asyncio.wait_for(case.probe.entered.wait(), 3)
    now = datetime.now(UTC)
    scheduled = JobRequest(
        request_id="scheduled-control",
        definition=definition,
        trigger=JobTriggerKind.SCHEDULED,
        scheduled_at=now,
        ready_at=now,
        attempt=1,
    )
    with case.app.state.application_context.execution():
        await case.runtime.requests.submit(scheduled, pending_limit=10)
        third = await case.service.trigger("job")
    case.probe.release.set()
    for identifier in (first, scheduled.request_id, third):
        await wait_state(case, identifier, "succeeded")
    assert case.probe.peak == 1
    assert len(case.probe.runs) == 3


@pytest.mark.parametrize("job_case", [{"owner": False, "capacity": 1}], indirect=True)
async def test_request_capacity_is_enforced_without_owner(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition())
        await case.service.trigger("job")
        with pytest.raises(JobException) as failure:
            await case.service.trigger("job")
        assert failure.value.reason == "capacity"
    assert not case.probe.runs


async def test_lease_loss_stops_new_execution(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition())
        client = case.runtime.cache.get_client(case.runtime.settings.owner_key())
        await client.set(case.runtime.lease.key, "different-owner", px=2000)
    async with asyncio.timeout(3):
        while case.runtime.owner:
            await asyncio.sleep(0.01)
    with case.app.state.application_context.execution():
        request = await case.service.trigger("job")
    async with case.engine.connect() as connection:
        assert (
            await connection.scalar(
                select(case.module.RequestRow.state).where(
                    case.module.RequestRow.request_key == request
                )
            )
            == "pending"
        )
    assert not case.probe.runs
