import pytest
from sqlalchemy import select

from .test_runtime import wait_state


@pytest.mark.parametrize("job_case", [{"tenant": True}], indirect=True)
async def test_fanout_uses_real_tenant_and_settles_each_target(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(fan_out=True))
        request = await case.service.trigger("job")
    await wait_state(case, request, "succeeded")
    assert case.probe.tenants == ["1", "2"]
    async with case.engine.connect() as connection:
        assert (await connection.scalars(select(case.module.TargetRow.state))).all() == [
            "completed",
            "completed",
        ]


@pytest.mark.parametrize("job_case", [{"tenant": True}], indirect=True)
async def test_success_with_settlement_failure_is_not_retried(job_case):
    case = job_case
    case.probe.settlement_failure = True
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(fan_out=True, max_retries=3))
        request = await case.service.trigger("job")
    await wait_state(case, request, "unknown")
    assert len(case.probe.runs) == 1
