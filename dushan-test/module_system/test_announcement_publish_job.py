from asyncio import CancelledError
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from sqlalchemy import and_

from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_job.public import JobContext, JobTriggerKind
from module_system.dal.dataobject.announcement.announcement_do import AnnouncementDO
from module_system.dal.mapper.announcement.announcement_mapper import AnnouncementMapper
from module_system.definitions.enums.announcement.announcement_status_enum import (
    AnnouncementStatusEnum,
)
from module_system.job.announcement import announcement_publish_job
from module_system.job.announcement.announcement_publish_job import AnnouncementPublishJob
from module_system.job.system_job_parameters import SystemJobParameters
from module_system.service.announcement.announcement_service_impl import AnnouncementServiceImpl

pytestmark = pytest.mark.unit


async def test_pending_query_requires_waiting_status_and_inclusive_due_time():
    """到期条件由 Mapper 同时约束待发布状态和包含边界的发布时间。"""
    now = datetime(2026, 10, 6, 12)
    mapper = AnnouncementMapper()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    mapper.read = AsyncMock(return_value=result)

    assert await mapper.select_pending_announcements(now) == []

    (statement,) = mapper.read.await_args.args
    assert statement.whereclause.compare(
        and_(
            AnnouncementDO.status == AnnouncementStatusEnum.WAIT_PUBLISH.code,
            AnnouncementDO.publish_time <= now,
        )
    )


async def test_due_publish_keeps_individual_transactions_and_idempotent_count(monkeypatch):
    """每条公告复用发布事务，已发布记录不重复通知且不计入发布数量。"""
    now = datetime(2026, 10, 6, 12)
    announcements = [
        AnnouncementDO(id=1, status=AnnouncementStatusEnum.WAIT_PUBLISH.code),
        AnnouncementDO(id=2, status=AnnouncementStatusEnum.PUBLISHED.code),
        AnnouncementDO(id=3, status=AnnouncementStatusEnum.WAIT_PUBLISH.code),
    ]
    boundaries = []

    @asynccontextmanager
    async def transaction(**options):
        """记录事务进出，不创建数据库连接。"""
        assert options == {"source": None, "propagation": "required"}
        boundaries.append("begin")
        yield
        boundaries.append("commit")

    monkeypatch.setattr(
        ApplicationContext, "lookup", Mock(return_value=SimpleNamespace(transaction=transaction))
    )
    service = AnnouncementServiceImpl()
    service.announcement_mapper = SimpleNamespace(
        select_pending_announcements=AsyncMock(return_value=announcements),
        select_for_update=AsyncMock(side_effect=announcements),
        update_by_id=AsyncMock(),
    )
    service._publish_announcement_notice = AsyncMock()

    assert await service.publish_due_announcements(now) == 2

    service.announcement_mapper.select_pending_announcements.assert_awaited_once_with(now)
    assert service.announcement_mapper.select_for_update.await_args_list == [
        call(1),
        call(2),
        call(3),
    ]
    assert service.announcement_mapper.update_by_id.await_args_list == [
        call(announcements[0]),
        call(announcements[2]),
    ]
    assert service._publish_announcement_notice.await_args_list == [
        call(announcements[0]),
        call(announcements[2]),
    ]
    assert boundaries == ["begin", "commit"] * 3


async def test_due_publish_without_candidates_returns_zero():
    """没有到期公告时不进入发布事务。"""
    service = AnnouncementServiceImpl()
    service.announcement_mapper = SimpleNamespace(
        select_pending_announcements=AsyncMock(return_value=[])
    )
    service.publish_announcement = AsyncMock()

    assert await service.publish_due_announcements(datetime(2026, 10, 6, 12)) == 0

    service.publish_announcement.assert_not_awaited()


@pytest.mark.parametrize("failure_type", [RuntimeError, CancelledError])
async def test_due_publish_propagates_failure_and_stops(failure_type):
    """发布失败或取消原样传播，不继续处理后续公告。"""
    service = AnnouncementServiceImpl()
    service.announcement_mapper = SimpleNamespace(
        select_pending_announcements=AsyncMock(
            return_value=[AnnouncementDO(id=1), AnnouncementDO(id=2), AnnouncementDO(id=3)]
        )
    )
    failure = failure_type("发布中止")
    service.publish_announcement = AsyncMock(side_effect=[True, failure, True])

    with pytest.raises(failure_type) as error:
        await service.publish_due_announcements(datetime(2026, 10, 6, 12))

    assert error.value is failure
    assert service.publish_announcement.await_args_list == [call(1), call(2)]


@pytest.mark.parametrize("failure_type", [None, RuntimeError, CancelledError])
async def test_announcement_job_delegates_publication_and_expiration(monkeypatch, failure_type):
    """任务以同一 UTC 时刻编排两项服务；发布失败时不执行过期处理。"""
    now = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
    clock = Mock()
    clock.now.return_value = now
    monkeypatch.setattr(announcement_publish_job, "datetime", clock)
    failure = None if failure_type is None else failure_type("发布中止")
    service = SimpleNamespace(
        publish_due_announcements=AsyncMock(return_value=2, side_effect=failure),
        expire_announcements=AsyncMock(return_value=3),
    )
    job = AnnouncementPublishJob()
    job.announcement_service = service
    context = JobContext(
        job_id="1",
        handler_key="system.announcement.publish",
        request_id="request-1",
        attempt=1,
        trigger=JobTriggerKind.MANUAL,
        scheduled_at=now,
        tenant_id="1",
    )

    if failure_type is None:
        assert (
            await job.execute(SystemJobParameters(), context)
            == "公告任务完成：发布 2 条，过期 3 条"
        )
        service.expire_announcements.assert_awaited_once_with(now.replace(tzinfo=None))
    else:
        with pytest.raises(failure_type) as error:
            await job.execute(SystemJobParameters(), context)
        assert error.value is failure
        service.expire_announcements.assert_not_awaited()

    service.publish_due_announcements.assert_awaited_once_with(now.replace(tzinfo=None))
    clock.now.assert_called_once_with(timezone.utc)
