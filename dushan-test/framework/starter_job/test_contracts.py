import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from framework.starter_job.core.job_registry import JobRegistry
from framework.starter_job.decorators.job import job
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.handler.job_handler import JobHandler

from .test_runtime import wait_state


def test_duplicate_keys_fail_and_parameters_are_explicit():
    class Parameters(BaseModel):
        value: int

    @job(key="same", parameters=Parameters, source="registered", capability="execute")
    class First(JobHandler):
        async def execute(self, parameters, context):
            return parameters.value

    @job(key="same", parameters=Parameters, source="registered", capability="execute")
    class Second(JobHandler):
        async def execute(self, parameters, context):
            return parameters.value

    with pytest.raises(JobException):
        JobRegistry([First, Second], "UTC")


async def test_http_returns_request_before_handler_finishes(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(parameters={"mode": "wait"}))
    async with AsyncClient(transport=ASGITransport(case.app), base_url="http://test") as client:
        response = await asyncio.wait_for(client.post("/test-jobs/trigger"), 3)
    request = response.json()["requestId"]
    await asyncio.wait_for(case.probe.entered.wait(), 3)
    assert case.probe.active == 1
    case.probe.release.set()
    await wait_state(case, request, "succeeded")


async def test_parameter_rejection_and_fail_closed_reconciliation(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        with pytest.raises(JobException):
            await case.service.save(case.definition(parameters={"unknown": 1}))
        definition = case.definition()
        await case.service.save(definition)
        assert case.runtime.scheduler.get_job("job") is not None
        await case.runtime.definitions.save_definition(
            definition.model_copy(update={"cron": "bad"})
        )
        with pytest.raises(ExceptionGroup):
            await case.runtime.reconcile()
        assert case.runtime.scheduler.get_job("job") is None


async def test_lease_loss_after_claim_does_not_start_handler(job_case):
    case = job_case
    case.probe.claim_wait = asyncio.Event()
    with case.app.state.application_context.execution():
        await case.service.save(case.definition())
        request = await case.service.trigger("job")
    await asyncio.wait_for(case.probe.claimed.wait(), 3)
    with case.app.state.application_context.execution():
        client = case.runtime.cache.get_client(case.runtime.settings.owner_key())
        await client.set(case.runtime.lease.key, "replacement-owner", px=2000)
    async with asyncio.timeout(2):
        while case.runtime.owner:
            await asyncio.sleep(0.01)
    case.probe.claim_wait.set()
    await wait_state(case, request, "pending")
    assert not case.probe.runs


async def test_unknown_business_effect_never_retries(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(parameters={"mode": "unknown"}, max_retries=3))
        request = await case.service.trigger("job")
    await wait_state(case, request, "unknown")
    assert case.probe.runs == [(request, 1)]
