from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from framework.common.exception import ServiceException
from framework.common.page import PageSettings
from framework.common.schemas.request import IdReqVO
from framework.starter_database.pagination.sql_paginator import SqlPaginator
from framework.starter_database.public import DatabaseSettings, SessionProvider
from module_infra.controller.admin.job.job_log_controller import JobLogController
from module_infra.controller.admin.job.vo.log.job_log_page_req_vo import JobLogPageReqVO
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.dal.dataobject.job.job_log_do import JobLogDO
from module_infra.dal.mapper.job.job_log_mapper import JobLogMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.job.job_log_service_impl import JobLogServiceImpl


@pytest.fixture
async def log_store(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'job-logs.sqlite').as_posix()}"
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            for model in (JobDO, JobLogDO):
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
        mapper = JobLogMapper()
        mapper.session_provider = database
        mapper.paginator = SqlPaginator(
            ConfigFactory.build(PageSettings, "page", fetch_all_enabled=True)
        )
        service = JobLogServiceImpl()
        service.job_log_mapper = mapper
        service.tenant = SimpleNamespace(get_required_tenant_id=lambda: "tenant-a")
        service.tenant_settings = SimpleNamespace(default_tenant_id="platform")
        now = datetime.now(UTC).replace(tzinfo=None)
        with database.scope():
            async with database.transaction() as session:
                for identifier, tenant_id in enumerate(
                    ("tenant-a", "tenant-b", "platform", None), start=1
                ):
                    session.add(
                        JobDO(
                            id=identifier,
                            name=f"任务 {identifier}",
                            status=1,
                            handler_name=f"test.log.{identifier}",
                            cron_expression="0 0 * * *",
                            revision="initial",
                            effective_at=now,
                            tenant_id=tenant_id,
                            fan_out=tenant_id is None,
                        )
                    )
                    session.add(
                        JobLogDO(
                            id=identifier,
                            job_id=identifier,
                            handler_name=f"test.log.{identifier}",
                            execute_index=1,
                            begin_time=now,
                            end_time=now,
                            duration=0,
                            status=1,
                            result=f"任务 {identifier} 的执行结果",
                            request_id=f"request-{identifier}",
                            state="succeeded",
                        )
                    )
            yield SimpleNamespace(service=service, database=database)
    finally:
        await database.close()


@pytest.mark.parametrize(
    "tenant_id,visible_ids",
    [("tenant-a", [1]), ("tenant-b", [2]), ("platform", [3, 4])],
)
@pytest.mark.parametrize("log_id", [1, 2, 3, 4, 99])
async def test_log_detail_uses_the_same_not_found_response_for_hidden_and_missing_logs(
    log_store, tenant_id, visible_ids, log_id
):
    service = log_store.service
    service.tenant.get_required_tenant_id = lambda: tenant_id
    request = IdReqVO(id=str(log_id))
    if log_id in visible_ids:
        response = await JobLogController.get_job_log(request, service)
        assert int(response.data.id) == log_id
    else:
        with pytest.raises(ServiceException) as error:
            await JobLogController.get_job_log(request, service)
        assert error.value.error_code == ErrorCodeConstants.JOB_LOG_NOT_EXISTS
        assert error.value.msg == "定时任务日志不存在"


@pytest.mark.parametrize(
    "tenant_id,expected", [("tenant-a", [1]), ("tenant-b", [2]), ("platform", [4, 3])]
)
@pytest.mark.parametrize("export", [False, True])
@pytest.mark.parametrize("filter_name", [None, "job_id", "handler_name"])
async def test_log_page_and_export_filter_tenant_scope_before_counting(
    log_store, tenant_id, expected, export, filter_name
):
    service = log_store.service
    service.tenant.get_required_tenant_id = lambda: tenant_id
    filters = {"job_id": "2", "handler_name": "test.log.2"}
    query = JobLogPageReqVO(**({filter_name: filters[filter_name]} if filter_name else {}))
    if export:
        query.enable_fetch_all(max_rows=100)
    if filter_name:
        expected = [identifier for identifier in expected if identifier == 2]
    result = await service.get_job_log_page(query)
    assert [row.id for row in result.items] == expected
    assert result.total == len(expected)


@pytest.mark.parametrize(
    "tenant_id,expected,total",
    [("tenant-a", [1], 1), ("tenant-b", [2], 1), ("platform", [4], 2)],
)
async def test_log_pagination_applies_scope_before_limit(log_store, tenant_id, expected, total):
    service = log_store.service
    service.tenant.get_required_tenant_id = lambda: tenant_id
    result = await service.get_job_log_page(JobLogPageReqVO(page_size=1))
    assert [row.id for row in result.items] == expected
    assert result.total == total


@pytest.mark.parametrize("tenant_id", ["tenant-a", "tenant-b", "platform"])
@pytest.mark.parametrize("job_id,owner", [(1, "tenant-a"), (4, "platform")])
async def test_deleted_job_logs_remain_visible_only_to_the_original_owner(
    log_store, tenant_id, job_id, owner
):
    async with log_store.database.transaction() as session:
        job = await session.get(JobDO, job_id)
        job.deleted = True
    service = log_store.service
    service.tenant.get_required_tenant_id = lambda: tenant_id
    expected = [job_id] if tenant_id == owner else []
    log = await service.get_job_log(job_id)
    assert ([] if log is None else [log.id]) == expected
    page = await service.get_job_log_page(JobLogPageReqVO(job_id=str(job_id)))
    assert [row.id for row in page.items] == expected
    assert page.total == len(expected)


@pytest.mark.parametrize("tenant_id", ["tenant-a", "tenant-b", "platform"])
@pytest.mark.parametrize("log_id", [1, 4])
async def test_deleted_logs_stay_hidden_even_when_the_job_is_deleted(log_store, tenant_id, log_id):
    async with log_store.database.transaction() as session:
        job = await session.get(JobDO, log_id)
        job.deleted = True
        log = await session.get(JobLogDO, log_id)
        log.deleted = True
    service = log_store.service
    service.tenant.get_required_tenant_id = lambda: tenant_id
    assert await service.get_job_log(log_id) is None
    page = await service.get_job_log_page(JobLogPageReqVO(job_id=str(log_id)))
    assert page.items == []
    assert page.total == 0
