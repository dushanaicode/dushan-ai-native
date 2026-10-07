import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from framework.starter_database.public import DatabaseSettings, SessionProvider
from framework.starter_job.core.job_runtime import JobRuntime
from framework.starter_job.model.job_outcome import JobOutcome
from framework.starter_job.public import (
    JobDefinition,
    JobErrorCodes,
    JobException,
    JobRequest,
    JobSettings,
    JobState,
    JobTriggerKind,
)
from module_infra.dal.dataobject.job.job_request_do import JobRequestDO
from module_infra.dal.dataobject.job.job_schedule_do import JobScheduleDO
from module_infra.dal.dataobject.job.job_signal_do import JobSignalDO
from module_infra.service.job.job_request_service_impl import JobRequestServiceImpl


@pytest.fixture
async def request_store(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'recovery.sqlite').as_posix()}"
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            for model in (JobRequestDO, JobScheduleDO, JobSignalDO):
                await connection.run_sync(model.__table__.create)
    finally:
        await engine.dispose()
    values = ConfigFactory.values()["config"]["models"]["database"]
    values.update(
        enabled=True,
        health_check_enabled=False,
        sources=[dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)],
    )
    database = SessionProvider(DatabaseSettings.model_validate(values))
    await database.open()
    try:
        with database.scope():
            store = JobRequestServiceImpl()
            store.database = database
            yield store
    finally:
        await database.close()


def request(identifier):
    now = datetime.now(UTC)
    definition = JobDefinition(
        id="1",
        handler_key="recovery",
        parameters={},
        cron="0 * * * *",
        enabled=True,
        revision="1",
        effective_at=now,
        max_instances=1,
        timeout_seconds=10.0,
        max_retries=1,
        retry_seconds=0.0,
        retry_backoff=1.0,
        stop_after_failure=False,
        tenant_id=None,
        fan_out=False,
    )
    return JobRequest(
        request_id=identifier,
        definition=definition,
        trigger=JobTriggerKind.MANUAL,
        scheduled_at=now,
        ready_at=now,
        attempt=1,
    )


async def test_retired_owner_can_settle_known_result_without_replaying_unknown(request_store):
    store = request_store
    first, second = request("first"), request("second")
    for item in (first, second):
        await store.submit(item, pending_limit=10)
    assert (
        await store.claim("old-owner", exclude_jobs=frozenset(), now=datetime.now(UTC))
    ).request_id == "first"
    assert (
        await store.claim("new-owner", exclude_jobs=frozenset(), now=datetime.now(UTC))
    ).request_id == "second"
    async with store.database.read_session(force_primary=True) as session:
        row = (
            await session.scalars(select(JobRequestDO).where(JobRequestDO.request_id == "first"))
        ).one()
        assert (row.state, row.owner) == ("unknown", "old-owner")
    with pytest.raises(JobException) as invalid:
        await store.finish("first", "new-owner", JobState.SUCCEEDED)
    assert invalid.value.error_code is JobErrorCodes.OWNER
    with pytest.raises(JobException):
        await store.retry(first, "old-owner")
    await store.finish("first", "old-owner", JobState.SUCCEEDED)
    await store.finish("second", "new-owner", JobState.SUCCEEDED)
    assert await store.claim("new-owner", exclude_jobs=frozenset(), now=datetime.now(UTC)) is None
    async with store.database.read_session(force_primary=True) as session:
        states = (
            await session.execute(
                select(JobRequestDO.request_id, JobRequestDO.state, JobRequestDO.owner).order_by(
                    JobRequestDO.request_id
                )
            )
        ).all()
        assert states == [("first", "succeeded", "old-owner"), ("second", "succeeded", "new-owner")]
    with pytest.raises(JobException):
        await store.finish("first", "old-owner", JobState.FAILED)


async def test_inflight_runtime_uses_original_token_after_real_store_takeover(request_store):
    store = request_store
    first, second = request("inflight"), request("next")
    for item in (first, second):
        await store.submit(item, pending_limit=10)
    claimed = await store.claim("old-owner", exclude_jobs=frozenset(), now=datetime.now(UTC))
    entered, release = asyncio.Event(), asyncio.Event()

    async def execute(*args):
        entered.set()
        await release.wait()
        return JobOutcome(JobState.SUCCEEDED)

    settings = JobSettings.model_validate(ConfigFactory.values()["config"]["models"]["job"])
    runtime = JobRuntime(
        settings,
        None,
        SimpleNamespace(timezone="UTC", validate=lambda value: None),
        SimpleNamespace(get_definition=AsyncMock(return_value=first.definition)),
        store,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    runtime.invoker = SimpleNamespace(invoke=execute)
    original = SimpleNamespace(owner_token="old-owner", is_valid=True)
    runtime.owner = runtime.accepting = True
    runtime.lease = original
    task = asyncio.create_task(runtime._execute_request(claimed, original))
    runtime.running[first.request_id] = (first.definition.id, task)
    runtime.counts[first.definition.id] = 1
    try:
        await asyncio.wait_for(entered.wait(), 2)
        next_request = await store.claim(
            "new-owner", exclude_jobs=frozenset(), now=datetime.now(UTC)
        )
        assert next_request.request_id == second.request_id
        runtime.lease = SimpleNamespace(owner_token="new-owner", is_valid=True)
        release.set()
        await asyncio.wait_for(task, 2)
        runtime._completed(first.request_id, task, original)
        assert runtime.owner and runtime.failure is None and not runtime.running
        await store.finish(second.request_id, "new-owner", JobState.SUCCEEDED)
        async with store.database.read_session(force_primary=True) as session:
            rows = (
                await session.execute(
                    select(
                        JobRequestDO.request_id, JobRequestDO.state, JobRequestDO.owner
                    ).order_by(JobRequestDO.request_id)
                )
            ).all()
            assert rows == [
                ("inflight", "succeeded", "old-owner"),
                ("next", "succeeded", "new-owner"),
            ]
        assert (
            await store.claim("new-owner", exclude_jobs=frozenset(), now=datetime.now(UTC)) is None
        )
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
