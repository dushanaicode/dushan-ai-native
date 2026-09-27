import asyncio
from dataclasses import replace
from datetime import UTC, datetime

from framework.starter_job.definitions.constants.job_error_codes import JobErrorCodes
from framework.starter_job.definitions.enums.job_state import JobState
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.model.job_outcome import JobOutcome
from framework.starter_tenant.spi.tenant_execution_provider import TenantExecutionProvider


class TenantJobRunner:
    def __init__(self, tenant: TenantExecutionProvider | None, targets, invoker, lease_seconds):
        self.tenant, self.targets, self.invoker, self.lease_seconds = (
            tenant,
            targets,
            invoker,
            lease_seconds,
        )

    async def run(self, request):
        if self.tenant is None or not self.tenant.ready or self.targets is None:
            raise JobException(JobErrorCodes.CONFIGURATION)
        ran = False
        failed = None
        observation_errors = []
        async for batch in self.tenant.target_batches():
            for tenant_id in batch:
                async with asyncio.timeout(self.invoker.settings.command_timeout_seconds):
                    lease = await self.targets.claim(
                        request.request_id, tenant_id, self.lease_seconds
                    )
                if lease is None:
                    continue
                if lease.request_id != request.request_id or lease.tenant_id != tenant_id:
                    raise JobException(JobErrorCodes.CONFIGURATION)
                if lease.expires_at <= datetime.now(UTC):
                    raise JobException(JobErrorCodes.OWNER)
                outcome = await self.invoker.invoke(request, tenant_id)
                observation_errors.extend(outcome.observation_errors)
                try:
                    async with asyncio.timeout(self.invoker.settings.command_timeout_seconds):
                        if outcome.state in {JobState.SUCCEEDED, JobState.SKIPPED}:
                            await self.targets.complete(lease)
                        elif outcome.state is not JobState.UNKNOWN:
                            await self.targets.release(lease)
                except Exception as error:
                    # 业务成功而结算未确认，禁止通过重试整个处理器掩盖控制面失败。
                    return JobOutcome(
                        JobState.UNKNOWN,
                        error=error,
                        observation_errors=tuple(observation_errors),
                    )
                ran = True
                if failed is None and outcome.state not in {JobState.SUCCEEDED, JobState.SKIPPED}:
                    failed = outcome
                if outcome.state in {JobState.UNKNOWN, JobState.CANCELLED}:
                    return replace(outcome, observation_errors=tuple(observation_errors))
        outcome = (
            failed
            if failed is not None
            else JobOutcome(JobState.SUCCEEDED if ran else JobState.SKIPPED)
        )
        return replace(outcome, observation_errors=tuple(observation_errors))
