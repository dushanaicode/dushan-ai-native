from asyncio import CancelledError
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_database.repository.base_mapper import BaseMapper
from module_infra.dal.mapper.job.job_log_mapper import JobLogMapper
from module_infra.dal.mapper.logger.api_access_log_mapper import ApiAccessLogMapper
from module_infra.dal.mapper.logger.api_error_log_mapper import ApiErrorLogMapper
from module_infra.service.job.job_log_service_impl import JobLogServiceImpl
from module_infra.service.logger.api_access_log_service_impl import ApiAccessLogServiceImpl
from module_infra.service.logger.api_error_log_service_impl import ApiErrorLogServiceImpl

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")

pytestmark = pytest.mark.unit

CLEANERS = [
    (ApiAccessLogServiceImpl, ApiAccessLogMapper, "api_access_log_mapper", "clean_access_log"),
    (ApiErrorLogServiceImpl, ApiErrorLogMapper, "api_error_log_mapper", "clean_error_log"),
    (JobLogServiceImpl, JobLogMapper, "job_log_mapper", "clean_job_log"),
]
NOW = datetime(2026, 10, 6, 12, 30, tzinfo=UTC)
EXPIRES = NOW.replace(tzinfo=None) - timedelta(days=14)


def cleanup_case(cleaner, batches, tenant_id="platform"):
    """使用真实 Service、Mapper 和批次入口，只替换数据库事务与会话。"""
    service_type, mapper_type, attribute, method = cleaner
    state = SimpleNamespace(active=False, include_deleted=False, events=[], selects=[], deletes=[])
    pending = iter(batches)

    @contextmanager
    def options(*, include_deleted):
        """记录软删除可见性选项的进入与释放。"""
        assert include_deleted is True
        assert state.include_deleted is False
        state.include_deleted = True
        try:
            yield
        finally:
            state.include_deleted = False

    async def scalars(statement):
        """截获真实选主键 SQL，并提供有界候选或批次故障。"""
        assert state.active and state.include_deleted
        state.selects.append(statement)
        batch = next(pending)
        if isinstance(batch, BaseException):
            raise batch
        return SimpleNamespace(all=lambda: batch)

    async def execute(statement):
        """截获真实删除 SQL，按选定主键返回影响条数。"""
        assert state.active and state.include_deleted
        state.deletes.append(statement)
        return SimpleNamespace(rowcount=len(statement.whereclause.right.value))

    @asynccontextmanager
    async def transaction(*, source):
        """记录各批事务独立结束，失败或取消时仅退出当前批。"""
        assert source is None
        assert state.active is False
        state.active = True
        state.events.append("begin")
        try:
            yield SimpleNamespace(scalars=scalars, execute=execute)
        except BaseException:
            state.events.append("rollback")
            raise
        else:
            state.events.append("commit")
        finally:
            state.active = False

    mapper = mapper_type()
    mapper.session_provider = SimpleNamespace(options=options, transaction=transaction)
    service = service_type()
    setattr(service, attribute, mapper)
    targets = AsyncMock(return_value=2)
    if service_type is JobLogServiceImpl:
        service.tenant = SimpleNamespace(get_required_tenant_id=lambda: tenant_id)
        service.tenant_settings = SimpleNamespace(default_tenant_id="platform")
        service.tenant_job_target_mapper = SimpleNamespace(delete_finished_before=targets)
    return SimpleNamespace(
        service=service, mapper=mapper, clean=getattr(service, method), state=state, targets=targets
    )


@pytest.mark.parametrize("cleaner", CLEANERS)
@pytest.mark.parametrize("batches", [[[]], [[1]], [[1, 2], [3]], [[1, 2], [3, 4], []]])
async def test_cleanup_uses_bounded_batches_and_releases_each_transaction(cleaner, batches):
    """覆盖空、半批、整批和多批累计，并保留台账的一次有界清理。"""
    case = cleanup_case(cleaner, batches)
    with patch(f"{cleaner[0].__module__}.datetime") as clock:
        clock.now.return_value = NOW
        count = await case.clean(14, 2)

    assert count == sum(map(len, batches)) + (2 if cleaner[0] is JobLogServiceImpl else 0)
    assert case.state.events == [event for _ in batches for event in ("begin", "commit")]
    assert case.state.active is False
    assert case.state.include_deleted is False
    assert len(case.state.selects) == len(batches)
    for statement in case.state.selects:
        assert statement._limit_clause.value == 2
        assert statement._for_update_arg.skip_locked is True
        assert [column.name for column in statement._order_by_clauses] == ["id"]
        assert statement.whereclause.compare(case.mapper.model.create_time < EXPIRES)
    assert [statement.whereclause.right.value for statement in case.state.deletes] == [
        batch for batch in batches if batch
    ]
    if cleaner[0] is JobLogServiceImpl:
        case.targets.assert_awaited_once_with(EXPIRES, 2)
    else:
        case.targets.assert_not_awaited()


@pytest.mark.parametrize("cleaner", CLEANERS)
@pytest.mark.parametrize("error_type", [RuntimeError, CancelledError])
async def test_cleanup_propagates_failed_batch_and_does_not_continue(cleaner, error_type):
    """前批完成后立即传播当前批故障或取消，不重试且不清理任务台账。"""
    error = error_type("batch interrupted")
    case = cleanup_case(cleaner, [[1, 2], error, [3]])
    with pytest.raises(error_type) as caught:
        await case.clean(14, 2)

    assert caught.value is error
    assert case.state.events == ["begin", "commit", "begin", "rollback"]
    assert len(case.state.deletes) == 1
    assert case.state.active is False
    assert case.state.include_deleted is False
    case.targets.assert_not_awaited()


async def test_ordinary_tenant_cleanup_does_not_touch_global_target_ledger():
    """普通租户完成日志清理后，不执行默认租户的全局台账清理。"""
    case = cleanup_case(CLEANERS[2], [[1, 2], [3]], tenant_id="tenant-a")
    assert await case.clean(14, 2) == 3
    case.targets.assert_not_awaited()


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
async def test_batch_cleanup_keeps_existing_limit_validation(limit):
    """复用原有单批参数校验，非法上限在进入事务前失败。"""
    case = cleanup_case(CLEANERS[0], [])
    with pytest.raises(ValueError, match="限定清理要求明确条件和正整数 limit"):
        await case.mapper.purge_in_batches_by_condition(case.mapper.model.id > 0, limit=limit)
    assert case.state.events == []


async def test_batch_cleanup_requires_explicit_conditions():
    """禁止无条件分批物理清理，沿用原有入口的安全校验。"""
    case = cleanup_case(CLEANERS[0], [])
    with pytest.raises(ValueError, match="限定清理要求明确条件和正整数 limit"):
        await BaseMapper.purge_in_batches_by_condition(case.mapper, limit=2)
    assert case.state.events == []
