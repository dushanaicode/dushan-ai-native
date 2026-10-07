from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from framework.starter_job.core.job_registry import JobRegistry
from framework.starter_job.definitions.constants.job_error_codes import JobErrorCodes
from framework.starter_job.public import JobException
from module_system.job.announcement.announcement_publish_job import AnnouncementPublishJob
from module_system.job.permission.permission_data_permission_sync_job import (
    PermissionDataPermissionSyncJob,
)
from module_system.job.system_job_parameters import SystemJobParameters


@pytest.mark.parametrize("handler", [AnnouncementPublishJob, PermissionDataPermissionSyncJob])
@pytest.mark.parametrize("parameters", [{"parameter": None}, {"parameter": "unused"}, {"other": 1}])
def test_system_jobs_accept_only_empty_parameters(handler, parameters):
    """两个无参数任务在框架输入边界拒绝所有未消费字段。"""
    registry = JobRegistry([handler], "UTC")
    definition = SimpleNamespace(handler_key=handler.__job__.key, parameters={})
    assert registry.parameters(definition).model_dump() == {}
    definition.parameters = parameters
    with pytest.raises(JobException) as caught:
        registry.parameters(definition)
    assert caught.value.error_code is JobErrorCodes.PARAMETERS


async def test_permission_sync_keeps_its_service_call_with_empty_parameters():
    """收紧参数合同后，权限同步仍执行原有缓存失效行为。"""
    handler = PermissionDataPermissionSyncJob()
    handler.publisher = SimpleNamespace(invalidate_all=AsyncMock())
    assert await handler.execute(SystemJobParameters(), None) == "数据权限同步任务完成"
    handler.publisher.invalidate_all.assert_awaited_once_with()
