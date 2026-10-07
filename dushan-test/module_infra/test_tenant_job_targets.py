import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pymysql
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from framework.common.dates import DateTimeOptions, DateUtils
from framework.starter_database.public import DatabaseSettings, SessionProvider
from framework.starter_job.core.tenant_job_runner import TenantJobRunner
from framework.starter_job.model.job_outcome import JobOutcome
from framework.starter_job.public import JobException, JobState
from framework.starter_tenant.core.tenant_execution_provider_adapter import (
    TenantExecutionProviderAdapter,
)
from framework.starter_tenant.core.tenant_service import TenantService
from framework.starter_tenant.public import TenantDirectoryProvider, TenantSettings
from module_infra.controller.admin.job.vo.job.job_resp_vo import JobRespVO
from module_infra.controller.admin.job.vo.job.job_save_req_vo import JobSaveReqVO
from module_infra.convert.job.job_convert import JobConvert
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.dal.dataobject.job.job_request_do import JobRequestDO
from module_infra.dal.dataobject.job.tenant_job_target_do import TenantJobTargetDO
from module_infra.dal.mapper.job.job_mapper import JobMapper
from module_infra.dal.mapper.job.tenant_job_target_mapper import TenantJobTargetMapper
from module_infra.service.job.job_definition_service_impl import JobDefinitionServiceImpl
from module_infra.service.job.job_service_impl import JobServiceImpl
from module_infra.spi.job import tenant_job_target_provider_adapter as adapter_module
from module_infra.spi.job.tenant_job_target_provider_adapter import TenantJobTargetProviderAdapter


class TestTenantJobTargets:
    @pytest.fixture(params=["sqlite", "mysql"])
    async def target_store(self, request, tmp_path):
        """创建独立数据库，验证真实事务和持久化状态。"""
        connection = None
        name = os.environ.get("DUSHAN_TEST_DATABASE_PREFIX", "tenant_job_test_") + uuid4().hex
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
            url = f"sqlite+aiosqlite:///{(tmp_path / 'targets.sqlite').as_posix()}"
        database = None
        try:
            engine = create_async_engine(url)
            try:
                async with engine.begin() as sql:
                    for model in (JobDO, JobRequestDO, TenantJobTargetDO):
                        await sql.run_sync(model.__table__.create)
            finally:
                await engine.dispose()
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
            mapper = TenantJobTargetMapper()
            mapper.session_provider = database
            adapter = TenantJobTargetProviderAdapter()
            adapter.mapper = mapper
            adapter.date_utils = DateUtils(ConfigFactory.build(DateTimeOptions, "datetime"))
            with database.scope():
                async with database.transaction() as session:
                    session.add(
                        JobRequestDO(
                            request_id="request",
                            job_id=1,
                            request={},
                            state="claimed",
                            owner="owner",
                            ready_at=datetime.now(UTC).replace(tzinfo=None),
                        )
                    )
                yield SimpleNamespace(database=database, adapter=adapter, dialect=request.param)
        finally:
            if database is not None:
                await database.close()
            if connection is not None:
                with connection.cursor() as cursor:
                    cursor.execute(f"DROP DATABASE `{name}`")
                connection.close()

    @staticmethod
    async def rows(store):
        """从主库读取目标状态，避免仅断言返回值。"""
        async with store.database.read_session(force_primary=True) as session:
            return (
                await session.scalars(
                    select(TenantJobTargetDO).order_by(TenantJobTargetDO.tenant_id)
                )
            ).all()

    async def test_claim_complete_skip_and_forged_lease(self, target_store):
        store = target_store
        lease = await store.adapter.claim("request", "tenant-a", 60)
        assert lease is not None
        assert await store.adapter.claim("request", "tenant-a", 60) is None
        with pytest.raises(JobException):
            await store.adapter.complete(lease.model_copy(update={"token": "forged"}))
        await store.adapter.complete(lease)
        assert await store.adapter.claim("request", "tenant-a", 60) is None
        assert (await self.rows(store))[0].state == "completed"

    async def test_release_allows_retry_with_new_token(self, target_store):
        store = target_store
        lease = await store.adapter.claim("request", "tenant-a", 60)
        await store.adapter.release(lease)
        assert (await self.rows(store))[0].state == "pending"
        next_lease = await store.adapter.claim("request", "tenant-a", 60)
        assert next_lease.token != lease.token
        with pytest.raises(JobException):
            await store.adapter.complete(lease)
        with pytest.raises(JobException):
            await store.adapter.release(lease)
        await store.adapter.complete(next_lease)
        assert (await self.rows(store))[0].state == "completed"

    async def test_expired_target_is_unknown_and_never_replayed(self, target_store, monkeypatch):
        store = target_store
        clock = Mock(wraps=datetime)
        clock.now.return_value = datetime(2026, 10, 4, tzinfo=UTC).replace(microsecond=123456)
        monkeypatch.setattr(adapter_module, "datetime", clock)
        lease = await store.adapter.claim("request", "tenant-a", 10.000001)
        assert (await self.rows(store))[0].expires_at_us % 1_000_000 == 123457
        clock.now.return_value = lease.expires_at
        with pytest.raises(JobException):
            await store.adapter.release(lease)
        assert await store.adapter.claim("request", "tenant-a", 60) is None
        assert (await self.rows(store))[0].state == "unknown"
        with pytest.raises(JobException):
            await store.adapter.release(lease)
        await store.adapter.complete(lease)
        assert (await self.rows(store))[0].state == "completed"
        assert await store.adapter.claim("request", "tenant-a", 60) is None

    async def test_claim_commits_independently_of_caller_rollback(self, target_store):
        store = target_store
        with pytest.raises(RuntimeError, match="业务回滚"):
            async with store.database.transaction():
                lease = await store.adapter.claim("request", "tenant-a", 60)
                raise RuntimeError("业务回滚")
        row = (await self.rows(store))[0]
        assert (row.state, row.token) == ("claimed", lease.token)

    async def test_concurrent_claim_has_one_owner(self, target_store):
        store = target_store
        if store.dialect == "sqlite":
            pytest.skip("并发认领依赖真实数据库行锁，在 MySQL 验证")
        leases = await asyncio.gather(
            *(store.adapter.claim("request", "tenant-a", 60) for _ in range(8))
        )
        owners = [lease for lease in leases if lease is not None]
        assert len(owners) == 1
        rows = await self.rows(store)
        assert len(rows) == 1 and rows[0].token == owners[0].token

    async def test_runner_uses_directory_and_skips_completed_on_retry(self, target_store):
        store = target_store
        values = ConfigFactory.values()["config"]["models"]["tenant"]
        values.update(enabled=True, target_batch_size=1)
        tenant = TenantService(TenantSettings.model_validate(values), None, None, store.database)
        directory = Mock(spec=TenantDirectoryProvider)
        directory.enabled_tenant_ids = AsyncMock(return_value=("tenant-a", "tenant-b"))
        tenant.directory, tenant.ready = directory, True
        invoker = SimpleNamespace(
            settings=SimpleNamespace(command_timeout_seconds=5),
            invoke=AsyncMock(
                side_effect=[JobOutcome(JobState.SUCCEEDED), JobOutcome(JobState.FAILED)]
            ),
        )
        runner = TenantJobRunner(TenantExecutionProviderAdapter(tenant), store.adapter, invoker, 60)
        request = SimpleNamespace(request_id="request")
        assert (await runner.run(request)).state is JobState.FAILED
        assert [call.args[1] for call in invoker.invoke.await_args_list] == ["tenant-a", "tenant-b"]
        assert [row.state for row in await self.rows(store)] == ["completed", "pending"]
        invoker.invoke = AsyncMock(return_value=JobOutcome(JobState.SUCCEEDED))
        assert (await runner.run(request)).state is JobState.SUCCEEDED
        assert [call.args[1] for call in invoker.invoke.await_args_list] == ["tenant-b"]
        assert (await runner.run(request)).state is JobState.SKIPPED
        assert directory.enabled_tenant_ids.await_count == 3

    async def test_management_switch_persists_both_target_modes(self, target_store):
        store = target_store
        manager = JobServiceImpl()
        manager.tenant = SimpleNamespace(get_required_tenant_id=lambda: "tenant-a")
        tenant_values = ConfigFactory.values()["config"]["models"]["tenant"]
        tenant_values["default_tenant_id"] = "tenant-a"
        manager.tenant_settings = TenantSettings.model_validate(tenant_values)
        request = JobSaveReqVO(
            name="按租户执行",
            handler_name="test.job",
            handler_param="{}",
            cron_expression="0 0 * * *",
            retry_count=0,
            retry_interval=0,
            fan_out=False,
        )
        initial = manager._row(request, 1, 1)
        mapper = JobMapper()
        mapper.session_provider = store.database
        await mapper.insert(initial)
        definitions = JobDefinitionServiceImpl()
        definitions.mapper = mapper
        for fan_out in (True, False):
            changed = manager._row(request.model_copy(update={"fan_out": fan_out}), 1, 1)
            async with store.database.transaction():
                await JobDefinitionServiceImpl.save_definition.__wrapped__(
                    definitions, JobConvert.to_job_definition(changed)
                )
            stored = await mapper.select_by_id(1)
            assert stored.fan_out is fan_out
            assert stored.tenant_id == (None if fan_out else "tenant-a")
            assert JobRespVO.model_validate(stored).model_dump(by_alias=True)["fanOut"] is fan_out
