import asyncio

from sqlalchemy import select


async def wait_state(case, request_id, expected):
    async with asyncio.timeout(8):
        while True:
            async with case.engine.connect() as connection:
                state = await connection.scalar(
                    select(case.module.RequestRow.state).where(
                        case.module.RequestRow.request_key == request_id
                    )
                )
            if state == expected:
                return
            await asyncio.sleep(0.01)


async def test_owner_manual_requests_execute_outside_caller(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition())
        request = await case.service.trigger("job")
    await wait_state(case, request, "succeeded")
    assert case.probe.runs == [(request, 1)]
    assert case.runtime.owner


async def test_retry_requeues_and_preserves_attempts(job_case):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(parameters={"mode": "retry"}, max_retries=1))
        request = await case.service.trigger("job")
    await wait_state(case, request, "succeeded")
    assert case.probe.runs == [(request, 1), (request, 2)]
