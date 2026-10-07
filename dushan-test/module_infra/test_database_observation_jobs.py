import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.starter_job.core.job_invoker import JobInvoker
from framework.starter_job.model.job_context import JobContext
from framework.starter_job.public import JobState, JobTriggerKind
from module_infra.job.data_source.database_health_job import DatabaseHealthJob
from module_infra.job.data_source.database_metrics_job import DatabaseMetricsJob
from module_infra.job.infra_observation_parameters import InfraObservationParameters
from module_infra.service.job.job_log_service_impl import JobLogServiceImpl


class TestDatabaseObservationJobs:
    @pytest.mark.parametrize(
        ("handler_type", "expected"),
        [
            (
                DatabaseHealthJob,
                {
                    "health": {"primary": True},
                    "replication": {"replica": {"healthy": True, "lag_seconds": 0}},
                },
            ),
            (
                DatabaseMetricsJob,
                {"primary": {"checked_out": 2}, "monitor": {"state": "正常"}},
            ),
        ],
    )
    async def test_structured_result_is_serialized_once_in_job_log(self, handler_type, expected):
        """数据库观测任务经调用器落日志后，结果文本只需解码一次。"""
        handler = handler_type()
        handler.database = SimpleNamespace(
            check_health=AsyncMock(return_value={"primary": True}),
            check_replication=AsyncMock(
                return_value={"replica": {"healthy": True, "lag_seconds": 0}}
            ),
            get_metrics=Mock(return_value=expected),
        )
        records = JobLogServiceImpl()
        records.job_log_mapper = SimpleNamespace(insert=AsyncMock())
        invoker = JobInvoker(
            application=None,
            security=None,
            registry=None,
            records=records,
            settings=SimpleNamespace(record_timeout_seconds=1, result_max_length=4096),
            monitor=None,
        )
        started = datetime.now(UTC)
        context = JobContext(
            job_id="1",
            handler_key=handler_type.__job__.key,
            request_id="database-observation",
            attempt=1,
            trigger=JobTriggerKind.MANUAL,
            scheduled_at=started,
            tenant_id=None,
        )
        request = SimpleNamespace(
            definition=SimpleNamespace(id=context.job_id, handler_key=context.handler_key),
            request_id=context.request_id,
            attempt=context.attempt,
            trigger=context.trigger,
        )

        outcome = await invoker._business(handler, InfraObservationParameters(), context, 1)
        assert outcome.state is JobState.SUCCEEDED
        await invoker.record(request, outcome, started, None)

        records.job_log_mapper.insert.assert_awaited_once()
        log = records.job_log_mapper.insert.call_args.args[0]
        assert json.loads(log.result) == expected
        assert outcome.result == expected
