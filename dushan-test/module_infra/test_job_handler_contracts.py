from contextlib import nullcontext
from contextvars import ContextVar
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.starter_job.core.job_invoker import JobInvoker
from framework.starter_job.core.job_registry import JobRegistry
from framework.starter_job.definitions.constants.job_error_codes import JobErrorCodes
from framework.starter_job.public import JobException, JobState, JobTriggerKind
from module_infra.job.data_source.database_health_job import DatabaseHealthJob
from module_infra.job.data_source.database_metrics_job import DatabaseMetricsJob
from module_infra.job.job.job_log_clean_job import JobLogCleanJob
from module_infra.job.logger.logger_access_log_clean_job import LoggerAccessLogCleanJob
from module_infra.job.logger.logger_error_log_clean_job import LoggerErrorLogCleanJob


class TestJobHandlerContracts:
    @pytest.mark.parametrize("handler_type", [DatabaseHealthJob, DatabaseMetricsJob])
    @pytest.mark.parametrize(
        "parameters", [{"retain_days": 7}, {"batch_size": 100}, {"parameter": "unused"}]
    )
    def test_observation_rejects_unused_parameters(self, handler_type, parameters):
        """观测计划只接受空输入，拒绝无效的清理字段和其他字段。"""
        registry = JobRegistry([handler_type], "UTC")
        definition = SimpleNamespace(handler_key=handler_type.__job__.key, parameters={})
        assert registry.parameters(definition).model_dump() == {}
        definition.parameters = parameters

        with pytest.raises(JobException) as caught:
            registry.parameters(definition)

        assert caught.value.error_code is JobErrorCodes.PARAMETERS

    @pytest.mark.parametrize(
        ("handler_type", "method", "default_days"),
        [
            (LoggerAccessLogCleanJob, "clean_access_log", 1),
            (LoggerErrorLogCleanJob, "clean_error_log", 14),
            (JobLogCleanJob, "clean_job_log", 14),
        ],
    )
    @pytest.mark.parametrize("parameters", [{}, {"retain_days": 7, "batch_size": 250}])
    async def test_cleanup_uses_declared_defaults_and_explicit_values(
        self, handler_type, method, default_days, parameters
    ):
        """省略参数保持各日志原有保留期，显式参数原样进入清理服务。"""
        registry = JobRegistry([handler_type], "UTC")
        definition = SimpleNamespace(handler_key=handler_type.__job__.key, parameters=parameters)
        model = registry.parameters(definition)
        expected_days = parameters.get("retain_days", default_days)
        expected_size = parameters.get("batch_size", 100)
        assert (model.retain_days, model.batch_size) == (expected_days, expected_size)
        handler = handler_type()
        clean = AsyncMock(return_value=3)
        handler.service = SimpleNamespace(**{method: clean})

        result = await handler.execute(model, SimpleNamespace(tenant_id="2"))

        clean.assert_awaited_once_with(expected_days, expected_size)
        assert "3 条" in result

    @pytest.mark.parametrize(
        "handler_type", [LoggerAccessLogCleanJob, LoggerErrorLogCleanJob, JobLogCleanJob]
    )
    @pytest.mark.parametrize(
        "parameters",
        [
            {"retain_days": None},
            {"retain_days": 0},
            {"retain_days": "14"},
            {"batch_size": None},
            {"batch_size": 0},
            {"batch_size": 1001},
        ],
    )
    def test_cleanup_rejects_null_and_invalid_limits(self, handler_type, parameters):
        """无效清理参数在调度校验阶段失败，不进入业务层补默认值。"""
        registry = JobRegistry([handler_type], "UTC")
        definition = SimpleNamespace(handler_key=handler_type.__job__.key, parameters=parameters)

        with pytest.raises(JobException) as caught:
            registry.parameters(definition)

        assert caught.value.error_code is JobErrorCodes.PARAMETERS

    @pytest.mark.parametrize("tenant_id", ["1", "2"])
    @pytest.mark.parametrize("failure", [False, True])
    @pytest.mark.parametrize(
        ("handler_type", "method", "retain_days"),
        [
            (JobLogCleanJob, "clean_job_log", 14),
            (LoggerAccessLogCleanJob, "clean_access_log", 1),
            (LoggerErrorLogCleanJob, "clean_error_log", 14),
        ],
    )
    async def test_cleanup_uses_invoker_identity(
        self, tenant_id, failure, handler_type, method, retain_days
    ):
        """三类日志沿用唯一调度身份，成功和失败均恢复进入前的租户上下文。"""
        tenant = ContextVar("job_test_tenant", default="outside")

        async def run_workload(source, callback, *, capability, tenant_id):
            """模拟调度器的工作负载进入与退出。"""
            assert (source, capability) == ("module_infra", handler_type.__job__.capability)
            token = tenant.set(tenant_id)
            try:
                return await callback()
            finally:
                tenant.reset(token)

        async def clean_job_log(retain_days, batch_size):
            """断言业务执行仍处于当前调度租户中。"""
            assert tenant.get() == tenant_id
            assert batch_size == 100
            if failure:
                raise RuntimeError("清理失败")
            return 2

        handler = handler_type()
        clean = AsyncMock(side_effect=clean_job_log)
        handler.service = SimpleNamespace(**{method: clean})
        security = SimpleNamespace(run_workload=AsyncMock(side_effect=run_workload))
        records = SimpleNamespace(record=AsyncMock())
        invoker = JobInvoker(
            application=SimpleNamespace(container=SimpleNamespace(get=Mock(return_value=handler))),
            security=security,
            registry=JobRegistry([handler_type], "UTC"),
            records=records,
            settings=SimpleNamespace(record_timeout_seconds=1, result_max_length=4096),
            monitor=SimpleNamespace(span=Mock(return_value=nullcontext())),
        )
        request = SimpleNamespace(
            definition=SimpleNamespace(
                id="1", handler_key=handler_type.__job__.key, parameters={}, timeout_seconds=1
            ),
            request_id="job-log-clean",
            attempt=1,
            trigger=JobTriggerKind.MANUAL,
            scheduled_at=datetime.now(UTC),
        )

        outcome = await invoker.invoke(request, tenant_id)

        assert outcome.state is (JobState.FAILED if failure else JobState.SUCCEEDED)
        if failure:
            assert isinstance(outcome.error, RuntimeError)
            assert str(outcome.error) == "清理失败"
        assert tenant.get() == "outside"
        security.run_workload.assert_awaited_once()
        clean.assert_awaited_once_with(retain_days, 100)
        records.record.assert_awaited_once()
        assert records.record.await_args.args[0].tenant_id == tenant_id
