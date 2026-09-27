import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from .test_runtime import wait_state


async def health(case):
    async with AsyncClient(
        transport=ASGITransport(app=case.app), base_url="http://testserver"
    ) as client:
        return await client.get("/health")


@pytest.mark.parametrize("job_case", [{"owner": False}], indirect=True)
async def test_client_role_is_healthy_without_local_scheduler(job_case):
    assert not job_case.runtime.owner and not job_case.runtime.scheduler.running
    response = await health(job_case)
    assert response.status_code == 200
    assert response.json()["data"]["components"]["job"] == "ready"


async def test_business_job_failure_does_not_mark_scheduler_unhealthy(job_case):
    with job_case.app.state.application_context.execution():
        await job_case.service.save(job_case.definition(parameters={"mode": "fail"}))
        request = await job_case.service.trigger("job")
    await wait_state(job_case, request, "failed")
    response = await health(job_case)
    assert response.status_code == 200
    assert response.json()["data"]["components"]["job"] == "ready"


async def test_definition_sync_failure_and_recovery_change_readiness(job_case, monkeypatch):
    async def broken_definition_source():
        raise ValueError("controlled invalid definitions")

    with monkeypatch.context() as patch:
        patch.setattr(job_case.runtime.definitions, "list_definitions", broken_definition_source)
        async with asyncio.timeout(3):
            while job_case.runtime.failure is None:
                await asyncio.sleep(0.01)
        assert not job_case.runtime._loop_task.done()
        response = await health(job_case)
        assert response.status_code == 503
        assert response.json()["data"]["components"]["job"] == "not_ready"
    async with asyncio.timeout(3):
        while job_case.runtime.failure is not None:
            await asyncio.sleep(0.01)
    assert (await health(job_case)).status_code == 200
