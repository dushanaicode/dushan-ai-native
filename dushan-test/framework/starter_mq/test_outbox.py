import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, update

from framework.starter_database.exception.after_commit_exception import AfterCommitException
from framework.starter_job.model.job_definition import JobDefinition
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.definitions.enums.outbox_state import OutboxState
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.outbox_record import OutboxRecord
from framework.starter_mq.model.publish_command import PublishCommand


async def enqueue(case, value, *, rollback=False):
    async def work():
        async with case.database.transaction() as session:
            await session.execute(insert(case.store_module.Business).values(name=str(value)))
            record_id = await case.outbox.enqueue(
                PublishCommand(
                    "events",
                    case.module.definition.mode,
                    case.module.Payload(value=value),
                    capability="mq:test",
                )
            )
            assert value not in case.probe.finished
            if rollback:
                raise ValueError("business rollback")
            return record_id

    return await case.app.state.security.run_workload("mq-test", work, capability="mq:test")


async def state_rows(case):
    async with case.engine.connect() as connection:
        return (
            await connection.execute(
                select(
                    case.store_module.Row.record_id,
                    case.store_module.Row.state,
                    case.store_module.Row.attempts,
                )
            )
        ).all()


async def test_business_commit_and_outbox_publish_share_transaction(mq_sql_case):
    case = mq_sql_case
    record_id = await enqueue(case, 1)
    await case.until(lambda: case.probe.finished == [1])
    assert await state_rows(case) == [(record_id, "published", 1)]
    with pytest.raises(ValueError, match="business rollback"):
        await enqueue(case, 2, rollback=True)
    async with case.engine.connect() as connection:
        assert (
            await connection.scalar(select(func.count()).select_from(case.store_module.Business))
            == 1
        )
        assert await connection.scalar(select(func.count()).select_from(case.store_module.Row)) == 1
    assert case.probe.finished == [1]


@pytest.mark.parametrize("mq_sql_options", [{"capacity": 1}], indirect=True)
async def test_after_commit_failure_keeps_business_and_job_retries_outbox(mq_sql_case):
    case = mq_sql_case
    await case.publish(0, behavior="wait")
    await case.until(lambda: case.probe.active == 1)
    with pytest.raises(AfterCommitException):
        await enqueue(case, 1)
    rows = await state_rows(case)
    assert len(rows) == 1 and rows[0].state == "pending" and rows[0].attempts == 1
    async with case.engine.connect() as connection:
        assert (
            await connection.scalar(select(func.count()).select_from(case.store_module.Business))
            == 1
        )
    case.probe.gate.set()
    await case.until(lambda: len(case.probe.records) == 1)
    # 精确推进到期边界，不靠固定长等待。
    async with case.engine.begin() as connection:
        await connection.execute(
            update(case.store_module.Row).values(
                ready=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
            )
        )
    definition = JobDefinition(
        id="outbox",
        handler_key="mq.outbox.dispatch",
        parameters={},
        cron="0 0 1 1 *",
        enabled=True,
        revision=uuid4().hex,
        effective_at=datetime.now(UTC),
        max_instances=1,
        timeout_seconds=10,
        max_retries=0,
        retry_seconds=1,
        retry_backoff=2,
        stop_after_failure=False,
        tenant_id=None,
        fan_out=False,
    )
    with case.app.state.application_context.execution():
        await case.job.save(definition)
        request_id = await case.job.trigger("outbox")
    await case.until(lambda: 1 in case.probe.finished)
    async with asyncio.timeout(5):
        while True:
            async with case.engine.connect() as connection:
                state = await connection.scalar(
                    select(case.job_module.RequestRow.state).where(
                        case.job_module.RequestRow.request_key == request_id
                    )
                )
            if state == "succeeded":
                break
            await asyncio.sleep(0)
    assert (await state_rows(case))[0].state == "published"


async def test_outbox_claims_are_exclusive_and_expiry_is_unknown(mq_sql_case):
    case = mq_sql_case
    prepared = await case.prepare(1)
    now = datetime.now(UTC)
    record = OutboxRecord(
        id=uuid4().hex,
        message=prepared,
        state=OutboxState.PENDING,
        attempts=0,
        created_at=now,
        ready_at=now,
        claim_token=None,
        claim_expires_at=None,
        finished_at=None,
        error_type=None,
    )

    async def create():
        async with case.database.transaction():
            await case.store.insert(record)

    await case.app.state.application_context.tasks.run_isolated(create)

    async def claim():
        return await case.store.claim(
            now=datetime.now(UTC), lease_seconds=30, max_attempts=2, record_id=None
        )

    values = await asyncio.gather(
        *(case.app.state.application_context.tasks.run_isolated(claim) for _ in range(2))
    )
    assert sum(value is not None for value in values) == 1
    async with case.engine.begin() as connection:
        await connection.execute(
            update(case.store_module.Row).values(
                expires=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
            )
        )
    assert await case.app.state.application_context.tasks.run_isolated(claim) is None
    assert (await state_rows(case))[0].state == "unknown"
    assert not case.probe.runs


async def test_publish_unknown_is_quarantined_after_committed_business(mq_sql_case, monkeypatch):
    case = mq_sql_case
    send = case.service.send_prepared

    async def uncertain(message):
        await send(message)
        raise MQException(MQErrorCodes.UNKNOWN)

    monkeypatch.setattr(case.service, "send_prepared", uncertain)
    with pytest.raises(AfterCommitException):
        await enqueue(case, 1)
    await case.until(lambda: len(case.probe.records) == 1)
    assert (await state_rows(case))[0].state == "unknown"
    result = await case.app.state.application_context.tasks.run_isolated(case.outbox.dispatch)
    assert sum(result.values()) == 0
    assert len(case.probe.runs) == 1
    removed = await case.app.state.application_context.tasks.run_isolated(
        lambda: case.store.cleanup(before=datetime.now(UTC) + timedelta(days=1), limit=10)
    )
    assert removed == 0


async def test_outbox_cancel_attempt_limit_and_bounded_retention(mq_sql_case):
    case = mq_sql_case
    prepared = await case.prepare(1)
    now = datetime.now(UTC)
    records = [
        OutboxRecord(
            id=str(index),
            message=prepared,
            state=OutboxState.PENDING,
            attempts=2 if index == 2 else 0,
            created_at=now,
            ready_at=now,
            claim_token=None,
            claim_expires_at=None,
            finished_at=None,
            error_type=None,
        )
        for index in (1, 2)
    ]

    async def work():
        async with case.database.transaction():
            for record in records:
                await case.store.insert(record)
        assert await case.store.cancel("1")
        assert not await case.store.cancel("1")
        assert (
            await case.store.claim(
                now=datetime.now(UTC), lease_seconds=30, max_attempts=2, record_id=None
            )
            is None
        )
        assert await case.store.cleanup(before=datetime.now(UTC) + timedelta(days=1), limit=1) == 1

    await case.app.state.application_context.tasks.run_isolated(work)
    rows = await state_rows(case)
    assert len(rows) == 1 and rows[0].state in {"cancelled", "dead"}
    assert not case.probe.runs


async def test_plain_after_commit_callback_preserves_commit_failure_semantics(
    mq_sql_case, monkeypatch
):
    case = mq_sql_case

    async def unavailable(*args):
        raise MQException(MQErrorCodes.CAPACITY)

    monkeypatch.setattr(case.runtime.backend, "publish", unavailable)

    async def work():
        async with case.database.transaction() as session:
            await session.execute(insert(case.store_module.Business).values(name="committed"))
            await case.service.publish_after_commit(
                PublishCommand(
                    "events",
                    case.module.definition.mode,
                    case.module.Payload(value=1),
                    capability="mq:test",
                )
            )

    with pytest.raises(AfterCommitException):
        await case.app.state.security.run_workload("mq-test", work, capability="mq:test")
    async with case.engine.connect() as connection:
        assert (
            await connection.scalar(select(func.count()).select_from(case.store_module.Business))
            == 1
        )
        assert await connection.scalar(select(func.count()).select_from(case.store_module.Row)) == 0
    assert not case.probe.runs
