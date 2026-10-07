from datetime import timezone

from framework.starter_job.public import (
    JobDefinition,
)
from module_infra.dal.dataobject.job.job_do import JobDO


class JobConvert:
    @staticmethod
    def to_job_definition(row: JobDO) -> JobDefinition:
        """把任务记录转换为调度运行时使用的任务定义，时间按 UTC 解释。"""
        return JobDefinition(
            id=str(row.id),
            handler_key=row.handler_name,
            parameters=row.parameters,
            cron=row.cron_expression,
            enabled=row.status == 1,
            revision=row.revision,
            effective_at=row.effective_at.replace(tzinfo=timezone.utc),
            max_instances=row.max_instances,
            timeout_seconds=float(row.timeout_seconds),
            max_retries=row.retry_count,
            retry_seconds=row.retry_interval / 1000,
            retry_backoff=float(row.retry_backoff),
            stop_after_failure=row.stop_after_failure,
            tenant_id=row.tenant_id,
            fan_out=row.fan_out,
        )
