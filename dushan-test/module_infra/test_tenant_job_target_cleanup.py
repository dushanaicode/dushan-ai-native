import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pymysql
import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from framework.common.dates import DateTimeOptions, DateUtils
from framework.starter_database.public import DatabaseSettings, SessionProvider
from module_infra.dal.dataobject.job.job_log_do import JobLogDO
from module_infra.dal.dataobject.job.job_request_do import JobRequestDO
from module_infra.dal.dataobject.job.tenant_job_target_do import TenantJobTargetDO
from module_infra.dal.mapper.job.job_log_mapper import JobLogMapper
from module_infra.dal.mapper.job.tenant_job_target_mapper import TenantJobTargetMapper
from module_infra.service.job.job_log_service_impl import JobLogServiceImpl
from module_infra.spi.job.tenant_job_target_provider_adapter import TenantJobTargetProviderAdapter


@pytest.fixture(params=["sqlite", "mysql"])
async def cleanup_store(request, tmp_path):
    connection = None
    name = "tenant_target_cleanup_" + uuid4().hex
    if request.param == "mysql":
        resource_path = os.environ.get("DUSHAN_SYSTEM_RESOURCES")
        if resource_path is None:
            pytest.skip("需要固定 MySQL 测试资源 DUSHAN_SYSTEM_RESOURCES")
        resources = json.loads(Path(resource_path).read_text(encoding="utf-8"))
        assert resources["mysql_port"] == 33170
        connection = pymysql.connect(
            host="127.0.0.1", port=33170, user="root", password="", autocommit=True
        )
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4")
        url = f"mysql+aiomysql://root@127.0.0.1:33170/{name}?charset=utf8mb4"
    else:
        url = f"sqlite+aiosqlite:///{(tmp_path / 'cleanup.sqlite').as_posix()}"
    engine = create_async_engine(url)
    database = None
    try:
        async with engine.begin() as sql:
            for model in (JobRequestDO, TenantJobTargetDO, JobLogDO):
                await sql.run_sync(model.__table__.create)
        values = ConfigFactory.values()["config"]["models"]["database"]
        values.update(
            enabled=True,
            health_check_enabled=False,
            sources=[
                dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)
            ],
        )
        database = SessionProvider(DatabaseSettings.model_validate(values))
        await database.open()
        targets = TenantJobTargetMapper()
        targets.session_provider = database
        logs = JobLogMapper()
        logs.session_provider = database
        service = JobLogServiceImpl()
        service.job_log_mapper = logs
        service.tenant_job_target_mapper = targets
        service.tenant = SimpleNamespace(get_required_tenant_id=lambda: "platform")
        service.tenant_settings = SimpleNamespace(default_tenant_id="platform")
        adapter = TenantJobTargetProviderAdapter()
        adapter.mapper = targets
        adapter.date_utils = DateUtils(ConfigFactory.build(DateTimeOptions, "datetime"))
        with database.scope():
            yield SimpleNamespace(
                engine=engine, database=database, service=service, targets=targets, adapter=adapter
            )
    finally:
        if database is not None:
            await database.close()
        await engine.dispose()
        if connection is not None:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE `{name}`")
            connection.close()


async def seed(store, identifier, parent_state, child_state, *, age=30):
    old = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=age)
    async with store.engine.begin() as sql:
        await sql.execute(
            insert(JobRequestDO).values(
                request_id=identifier,
                job_id=1,
                request={},
                state=parent_state,
                owner="owner",
                ready_at=old,
                create_time=old,
                update_time=old,
            )
        )
        await sql.execute(
            insert(TenantJobTargetDO).values(
                request_id=identifier,
                tenant_id="tenant-a",
                state=child_state,
                token="original",
                expires_at_us=0,
                create_time=old,
                update_time=old,
            )
        )


async def target_ids(store):
    async with store.database.read_session(force_primary=True) as session:
        return set(await session.scalars(select(TenantJobTargetDO.request_id)))


@pytest.mark.parametrize(
    "parent_state", ["succeeded", "failed", "skipped", "cancelled", "timed_out"]
)
async def test_cleanup_removes_only_expired_final_targets_and_keeps_parent_tombstone(
    cleanup_store, parent_state
):
    store = cleanup_store
    await seed(store, "expired", parent_state, "completed")
    await seed(store, "recent", parent_state, "completed", age=1)
    assert await store.service.clean_job_log(14, 10) == 1
    assert await target_ids(store) == {"recent"}
    async with store.database.read_session(force_primary=True) as session:
        assert set(await session.scalars(select(JobRequestDO.request_id))) == {"expired", "recent"}
    assert await store.adapter.claim("expired", "tenant-a", 60) is None
    assert await target_ids(store) == {"recent"}


async def test_cleanup_preserves_retry_unknown_and_inflight_targets_and_is_bounded(cleanup_store):
    store = cleanup_store
    for parent in ("pending", "claimed", "unknown"):
        for child in ("completed", "pending", "unknown", "claimed"):
            await seed(store, parent + child, parent, child)
    for child in ("unknown", "claimed"):
        await seed(store, "final" + child, "failed", child)
    protected = await target_ids(store)
    for index in range(3):
        await seed(store, f"expired{index}", "failed", "pending")
    assert await store.service.clean_job_log(14, 2) == 2
    assert len(await target_ids(store)) == len(protected) + 1
    assert await store.service.clean_job_log(14, 2) == 1
    assert await target_ids(store) == protected
    assert await store.service.clean_job_log(14, 2) == 0


@pytest.mark.parametrize(
    "parent_state",
    ["pending", "succeeded", "failed", "skipped", "cancelled", "timed_out", "unknown"],
)
async def test_only_claimed_parent_can_issue_a_new_target_lease(cleanup_store, parent_state):
    store = cleanup_store
    await seed(store, "request", parent_state, "pending")
    assert await store.adapter.claim("request", "tenant-a", 60) is None
    assert await store.adapter.claim("request", "new-tenant", 60) is None


async def test_ordinary_tenant_cleanup_cannot_purge_global_target_ledger(cleanup_store):
    store = cleanup_store
    await seed(store, "expired", "succeeded", "completed")
    store.service.tenant.get_required_tenant_id = lambda: "tenant-a"
    assert await store.service.clean_job_log(14, 10) == 0
    assert await target_ids(store) == {"expired"}
