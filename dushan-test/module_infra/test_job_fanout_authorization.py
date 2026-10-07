import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pymysql
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from framework.common.exception import ServiceException
from framework.common.page import PageSettings
from framework.common.schemas.request import IdReqVO
from framework.starter_database.pagination.sql_paginator import SqlPaginator
from framework.starter_database.public import DatabaseSettings, SessionProvider
from framework.starter_di.public import ApplicationContext
from framework.starter_job.core.tenant_job_runner import TenantJobRunner
from framework.starter_job.model.job_outcome import JobOutcome
from framework.starter_job.public import JobState, TenantJobLease
from framework.starter_tenant.public import TenantSettings
from framework.starter_web.public import RoutePolicy
from module_infra.controller.admin.job.job_controller import JobController
from module_infra.controller.admin.job.vo.job.job_export_req_vo import JobExportReqVO
from module_infra.controller.admin.job.vo.job.job_next_times_req_vo import JobNextTimesReqVO
from module_infra.controller.admin.job.vo.job.job_page_req_vo import JobPageReqVO
from module_infra.controller.admin.job.vo.job.job_save_req_vo import JobSaveReqVO
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.dal.mapper.job.job_mapper import JobMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.job.job_service_impl import JobServiceImpl


@pytest.fixture
def manager(monkeypatch):
    service = JobServiceImpl()
    values = ConfigFactory.values()["config"]["models"]["tenant"]
    values["default_tenant_id"] = "platform"
    service.tenant_settings = TenantSettings.model_validate(values)
    service.tenant = SimpleNamespace(get_required_tenant_id=Mock(return_value="tenant-a"))
    service.mapper = SimpleNamespace(
        select_by_id=AsyncMock(),
        select_for_update=AsyncMock(),
        select_by_handler_name=AsyncMock(return_value=None),
        insert=AsyncMock(),
        update_by_id=AsyncMock(),
    )

    @asynccontextmanager
    async def transaction(**kwargs):
        yield

    service.database = SimpleNamespace(next_id=Mock(return_value=1), transaction=transaction)
    monkeypatch.setattr(ApplicationContext, "lookup", lambda _: service.database)
    service.native = SimpleNamespace(save=AsyncMock(), trigger=AsyncMock(), delete=AsyncMock())
    return service


def form(*, fan_out=True, identifier=None):
    return JobSaveReqVO(
        id=identifier,
        name="按租户执行",
        handler_name="infra.log.access.clean",
        handler_param="{}",
        fan_out=fan_out,
        cron_expression="0 0 * * *",
        retry_count=0,
        retry_interval=0,
    )


def stored_job(manager, *, fan_out=True, status=1):
    row = manager._row(form(fan_out=False), 1, status)
    row.fan_out = fan_out
    row.tenant_id = None if fan_out else manager.tenant.get_required_tenant_id()
    manager.mapper.select_by_id.return_value = row
    manager.mapper.select_for_update.return_value = row
    manager.mapper.select_by_handler_name.return_value = row
    return row


async def mutate(manager, operation, *, fan_out):
    arguments = {
        "update_job": (form(fan_out=fan_out, identifier="1"),),
        "delete_job": (1,),
        "delete_job_batch": ([1],),
        "trigger_job": (1,),
        "trigger_job_by_handler": ("infra.log.access.clean", "{}"),
        "update_job_status": (1, 2),
        "enable_job": (1, 1),
    }
    method = "update_job_status" if operation == "enable_job" else operation
    return await getattr(manager, method)(*arguments[operation])


def assert_no_writes(manager):
    for method in (
        manager.mapper.insert,
        manager.mapper.update_by_id,
        manager.native.save,
        manager.native.trigger,
        manager.native.delete,
    ):
        method.assert_not_awaited()


def test_review_reproducer_cannot_materialize_fanout_for_tenant_admin(manager):
    policy = getattr(JobController.create_job, RoutePolicy.ATTRIBUTE)
    assert policy.realm.value == "tenant"
    assert policy.permissions == ("infra:job:create",)
    assert policy.roles == () and policy.required_capability is None
    with pytest.raises(ServiceException) as error:
        manager._row(form(), 1, 1)
    assert error.value.error_code.code == 1001001012


@pytest.mark.parametrize("locale", ["zh-CN", "en-US"])
def test_fanout_authorization_error_has_localized_message(locale):
    error = ErrorCodeConstants.JOB_FAN_OUT_DEFAULT_TENANT_ONLY
    assert error.code == 1001001012
    assert error.message_key == "infra.job.fan_out_default_tenant_only"
    resources = (
        Path(__file__).resolve().parents[2] / "dushan-admin-backend/module_infra/definitions/i18n"
    )
    messages = json.loads((resources / f"{locale}.json").read_text(encoding="utf-8"))
    assert messages["infra"]["job"]["fan_out_default_tenant_only"]


async def test_tenant_admin_cannot_create_fanout(manager):
    with pytest.raises(ServiceException) as error:
        await manager.create_job(form())
    assert error.value.error_code.code == 1001001012
    assert_no_writes(manager)


@pytest.mark.parametrize(
    "operation",
    [
        "update_job",
        "delete_job",
        "delete_job_batch",
        "trigger_job",
        "trigger_job_by_handler",
        "update_job_status",
        "enable_job",
    ],
)
async def test_tenant_admin_cannot_mutate_existing_fanout(manager, operation):
    stored_job(manager, status=2 if operation == "enable_job" else 1)
    with pytest.raises(ServiceException) as error:
        await mutate(manager, operation, fan_out=False)
    assert error.value.error_code == ErrorCodeConstants.JOB_NOT_EXISTS
    assert_no_writes(manager)


async def test_tenant_admin_cannot_promote_ordinary_job_to_fanout(manager):
    stored_job(manager, fan_out=False)
    with pytest.raises(ServiceException) as error:
        await mutate(manager, "update_job", fan_out=True)
    assert error.value.error_code.code == 1001001012
    assert_no_writes(manager)


@pytest.mark.parametrize(
    "operation",
    [
        "update_job",
        "delete_job",
        "delete_job_batch",
        "trigger_job",
        "trigger_job_by_handler",
        "update_job_status",
        "enable_job",
    ],
)
async def test_mutations_authorize_current_primary_scope_not_stale_replica(manager, operation):
    current = stored_job(manager, status=2 if operation == "enable_job" else 1)
    stale = manager._row(form(fan_out=False), 1, current.status)
    manager.mapper.select_by_id.return_value = stale
    manager.mapper.select_by_handler_name.return_value = stale
    with pytest.raises(ServiceException) as error:
        await mutate(manager, operation, fan_out=False)
    assert error.value.error_code == ErrorCodeConstants.JOB_NOT_EXISTS
    assert_no_writes(manager)


@pytest.mark.parametrize(
    "tenant_id,fan_out", [("platform", True), ("platform", False), ("tenant-a", False)]
)
async def test_authorized_create_preserves_target_scope(manager, tenant_id, fan_out):
    manager.tenant.get_required_tenant_id.return_value = tenant_id
    assert await manager.create_job(form(fan_out=fan_out)) == 1
    row = manager.mapper.insert.await_args.args[0]
    assert row.tenant_id == (None if fan_out else tenant_id)
    assert row.fan_out is fan_out
    manager.native.save.assert_awaited_once()


@pytest.mark.parametrize(
    "operation",
    [
        "update_job",
        "delete_job",
        "delete_job_batch",
        "trigger_job",
        "trigger_job_by_handler",
        "update_job_status",
        "enable_job",
    ],
)
@pytest.mark.parametrize("tenant_id,fan_out", [("platform", True), ("tenant-a", False)])
async def test_authorized_mutations_remain_available(manager, tenant_id, fan_out, operation):
    manager.tenant.get_required_tenant_id.return_value = tenant_id
    stored_job(manager, fan_out=fan_out, status=2 if operation == "enable_job" else 1)
    await mutate(manager, operation, fan_out=fan_out)
    assert (
        sum(
            method.await_count
            for method in (manager.native.save, manager.native.trigger, manager.native.delete)
        )
        == 1
    )


async def test_default_tenant_can_switch_both_directions(manager):
    manager.tenant.get_required_tenant_id.return_value = "platform"
    for old_mode, new_mode in ((False, True), (True, False)):
        stored_job(manager, fan_out=old_mode)
        await mutate(manager, "update_job", fan_out=new_mode)
        definition = manager.native.save.await_args.args[0]
        assert definition.fan_out is new_mode
        assert definition.tenant_id == (None if new_mode else "platform")


@pytest.mark.parametrize("tenant_id,visible", [("platform", True), ("tenant-a", False)])
async def test_detail_hides_global_jobs_outside_default_tenant(manager, tenant_id, visible):
    row = stored_job(manager)
    manager.tenant.get_required_tenant_id.return_value = tenant_id
    assert await manager.get_job(1) is (row if visible else None)


@pytest.fixture(params=["sqlite", "mysql"])
async def persisted_manager(manager, tmp_path, request):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'jobs.sqlite').as_posix()}"
    connection = None
    if request.param == "mysql":
        resource_path = os.environ.get("DUSHAN_SYSTEM_RESOURCES")
        if resource_path is None:
            pytest.skip("需要独立随机测试库所在的 MySQL 资源清单")
        resources = json.loads(Path(resource_path).read_text(encoding="utf-8"))
        assert resources["mysql_port"] == 33170
        connection = pymysql.connect(
            host="127.0.0.1", port=33170, user="root", password="", autocommit=True
        )
        database_name = "job_authorization_" + uuid4().hex
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4")
        url = f"mysql+aiomysql://root@127.0.0.1:33170/{database_name}?charset=utf8mb4"
    database = None
    try:
        engine = create_async_engine(url)
        try:
            async with engine.begin() as sql:
                await sql.run_sync(JobDO.__table__.create)
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
        with database.scope():
            async with database.transaction() as session:
                for identifier, fan_out in ((1, False), (2, True)):
                    row = manager._row(form(fan_out=False), identifier, 1)
                    row.handler_name = f"test.job.{identifier}"
                    row.tenant_id = None if fan_out else "tenant-a"
                    row.fan_out = fan_out
                    session.add(row)
            mapper = JobMapper()
            mapper.session_provider = database
            mapper.paginator = SqlPaginator(
                ConfigFactory.build(PageSettings, "page", fetch_all_enabled=True)
            )
            manager.mapper = mapper
            manager.database = database
            yield manager
    finally:
        if database is not None:
            await database.close()
        if connection is not None:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE `{database_name}`")
            connection.close()


@pytest.mark.parametrize("export", [False, True])
@pytest.mark.parametrize("tenant_id,expected", [("platform", [2]), ("tenant-a", [1])])
async def test_page_and_export_filter_global_jobs_before_pagination(
    persisted_manager, tenant_id, expected, export
):
    persisted_manager.tenant.get_required_tenant_id.return_value = tenant_id
    query = JobExportReqVO() if export else JobPageReqVO()
    if export:
        query.enable_fetch_all(max_rows=100)
    result = await persisted_manager.get_job_page(query)
    assert sorted(row.id for row in result.items) == expected
    assert result.total == len(expected)


@pytest.mark.parametrize("tenant_id,allowed", [("platform", True), ("tenant-a", False)])
async def test_persisted_scope_is_locked_before_manual_trigger(
    persisted_manager, tenant_id, allowed
):
    persisted_manager.tenant.get_required_tenant_id.return_value = tenant_id
    if allowed:
        await persisted_manager.trigger_job(2)
        persisted_manager.native.trigger.assert_awaited_once_with("2")
    else:
        with pytest.raises(ServiceException) as error:
            await persisted_manager.trigger_job(2)
        assert error.value.error_code == ErrorCodeConstants.JOB_NOT_EXISTS
        persisted_manager.native.trigger.assert_not_awaited()


@pytest.mark.parametrize("persisted_manager", ["mysql"], indirect=True)
async def test_locked_authorization_refreshes_previously_loaded_identity(persisted_manager):
    manager = persisted_manager
    with pytest.raises(ServiceException) as error:
        async with manager.database.transaction():
            stale = await manager.mapper.select_by_id(1)
            assert stale.fan_out is False
            async with manager.database.transaction(propagation="requires_new") as session:
                current = await session.scalar(select(JobDO).where(JobDO.id == 1))
                current.fan_out, current.tenant_id = True, None
            await manager.trigger_job(1)
    assert error.value.error_code == ErrorCodeConstants.JOB_NOT_EXISTS
    manager.native.trigger.assert_not_awaited()


@pytest.mark.parametrize("tenant_id", ["tenant-a", "platform"])
@pytest.mark.parametrize(
    "operation",
    [
        "detail",
        "next_times",
        "update_job",
        "delete_job",
        "delete_job_batch",
        "trigger_job",
        "trigger_job_by_handler",
        "update_job_status",
        "enable_job",
    ],
)
async def test_other_tenant_job_is_indistinguishable_from_missing(
    persisted_manager, tenant_id, operation
):
    manager = persisted_manager
    async with manager.database.transaction() as session:
        row = await session.scalar(select(JobDO).where(JobDO.id == 1))
        row.tenant_id = "tenant-b"
        row.handler_name = "infra.log.access.clean"
        row.status = 2 if operation == "enable_job" else 1
    manager.tenant.get_required_tenant_id.return_value = tenant_id
    with pytest.raises(ServiceException) as error:
        if operation == "detail":
            await JobController.get_job(IdReqVO(id="1"), manager)
        elif operation == "next_times":
            await JobController.get_job_next_times(
                JobNextTimesReqVO(id="1", count=1),
                manager,
                SimpleNamespace(),
                SimpleNamespace(timezone="UTC"),
            )
        else:
            await mutate(manager, operation, fan_out=False)
    assert error.value.error_code == ErrorCodeConstants.JOB_NOT_EXISTS
    for method in (manager.native.save, manager.native.trigger, manager.native.delete):
        method.assert_not_awaited()


@pytest.mark.parametrize("tenant_id", ["tenant-a", "platform"])
@pytest.mark.parametrize("export", [False, True])
async def test_page_and_export_exclude_other_tenant_before_count_and_limit(
    persisted_manager, tenant_id, export
):
    manager = persisted_manager
    async with manager.database.transaction() as session:
        for identifier, owner in ((3, "tenant-b"), (4, "platform")):
            row = manager._row(form(fan_out=False), identifier, 1)
            row.handler_name = f"test.job.{identifier}"
            row.tenant_id = owner
            session.add(row)
    manager.tenant.get_required_tenant_id.return_value = tenant_id
    query = JobExportReqVO() if export else JobPageReqVO(page_size=1)
    if export:
        query.enable_fetch_all(max_rows=100)
    expected = {2, 4} if tenant_id == "platform" else {1}
    result = await manager.get_job_page(query)
    assert result.total == len(expected)
    assert {row.id for row in result.items} <= expected
    assert len(result.items) == (len(expected) if export else 1)


async def test_mixed_batch_checks_all_owners_before_deleting(persisted_manager):
    manager = persisted_manager
    async with manager.database.transaction() as session:
        row = manager._row(form(fan_out=False), 3, 1)
        row.handler_name = "test.job.3"
        row.tenant_id = "tenant-b"
        session.add(row)
    with pytest.raises(ServiceException) as error:
        await manager.delete_job_batch([1, 3])
    assert error.value.error_code == ErrorCodeConstants.JOB_NOT_EXISTS
    manager.native.delete.assert_not_awaited()


@pytest.mark.parametrize("operation", ["create", "update"])
async def test_handler_uniqueness_is_global_without_disclosing_owner(manager, operation):
    own = stored_job(manager, fan_out=False)
    other = manager._row(form(fan_out=False), 2, 1)
    other.tenant_id = "tenant-b"
    other.name = "private job name"
    manager.mapper.select_by_handler_name.return_value = other
    with pytest.raises(ServiceException) as error:
        if operation == "create":
            await manager.create_job(form(fan_out=False))
        else:
            await manager.update_job(form(fan_out=False, identifier=str(own.id)))
    assert error.value.error_code == ErrorCodeConstants.JOB_HANDLER_EXISTS
    assert "tenant-b" not in str(error.value)
    assert "private job name" not in str(error.value)
    assert_no_writes(manager)


async def test_default_tenant_fanout_still_executes_each_tenant(manager):
    manager.tenant.get_required_tenant_id.return_value = "platform"
    assert manager._row(form(), 1, 1).tenant_id is None

    async def batches():
        yield ("tenant-a", "tenant-b")

    async def claim(request_id, tenant_id, lease_seconds):
        return TenantJobLease(
            request_id=request_id,
            tenant_id=tenant_id,
            token=tenant_id,
            expires_at=datetime.now(UTC) + timedelta(seconds=lease_seconds),
        )

    invoker = SimpleNamespace(
        settings=SimpleNamespace(command_timeout_seconds=1),
        invoke=AsyncMock(return_value=JobOutcome(JobState.SUCCEEDED)),
    )
    runner = TenantJobRunner(
        SimpleNamespace(ready=True, target_batches=batches),
        SimpleNamespace(claim=claim, complete=AsyncMock(), release=AsyncMock()),
        invoker,
        30,
    )
    assert (await runner.run(SimpleNamespace(request_id="proof"))).state is JobState.SUCCEEDED
    assert [call.args[1] for call in invoker.invoke.await_args_list] == ["tenant-a", "tenant-b"]
