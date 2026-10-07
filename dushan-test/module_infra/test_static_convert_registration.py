from datetime import UTC, datetime
from types import SimpleNamespace

from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata
from module_infra.convert.cache.cache_convert import CacheConvert
from module_infra.convert.job.job_convert import JobConvert


def test_cache_conversion_remains_direct_without_a_di_registration():
    """无状态缓存转换直接按类调用且不占用容器注册。"""
    assert DiComponentMetadata.ATTRIBUTE not in vars(CacheConvert)
    result = CacheConvert.build_monitor_info(
        {"redis_version": "7"}, 3, {"cmdstat_get": {"calls": "5", "usec": "8"}}
    )
    assert result.info == {"redis_version": "7"}
    assert result.db_size == 3
    assert [(stat.command, stat.calls, stat.usec) for stat in result.command_stats] == [
        ("get", 5, 8)
    ]


def test_job_conversion_remains_direct_without_a_di_registration():
    """任务转换保留 UTC、重试单位和租户合同，不需要容器实例。"""
    assert DiComponentMetadata.ATTRIBUTE not in vars(JobConvert)
    effective_at = datetime(2026, 1, 1)
    row = SimpleNamespace(
        id=1,
        handler_name="system.permission.sync",
        parameters={},
        cron_expression="0 4 * * *",
        status=1,
        revision="r1",
        effective_at=effective_at,
        max_instances=1,
        timeout_seconds=30,
        retry_count=2,
        retry_interval=1250,
        retry_backoff=2,
        stop_after_failure=False,
        tenant_id="2",
        fan_out=False,
    )
    result = JobConvert.to_job_definition(row)
    assert result.effective_at == effective_at.replace(tzinfo=UTC)
    assert result.retry_seconds == 1.25
    assert (result.id, result.tenant_id, result.parameters) == ("1", "2", {})
