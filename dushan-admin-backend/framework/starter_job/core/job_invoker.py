import asyncio
import inspect
import json
from datetime import UTC, datetime

from framework.common.security.sanitizer import Sanitizer
from framework.common.utils.asyncio_utils import AsyncioUtils
from framework.starter_database.exception.after_commit_exception import AfterCommitException
from framework.starter_job.definitions.enums.job_state import JobState
from framework.starter_job.exception.job_result_unknown import JobResultUnknown
from framework.starter_job.model.job_context import JobContext
from framework.starter_job.model.job_outcome import JobOutcome
from framework.starter_job.model.job_record import JobRecord


class JobInvoker:
    """一次尝试的业务、线程与观测终态；没有 HTTP 等待或进程内重试循环。"""

    def __init__(self, application, security, registry, records, settings, monitor):
        self.application, self.security, self.registry = application, security, registry
        self.records, self.settings = records, settings
        self.monitor = monitor
        self.running_threads = 0
        self.timed_out_threads = 0

    async def invoke(self, request, tenant_id):
        started = datetime.now(UTC)
        handler_type = self.registry.require(request.definition.handler_key)
        declaration = handler_type.__job__
        context = JobContext(
            request.definition.id,
            declaration.key,
            request.request_id,
            request.attempt,
            request.trigger,
            request.scheduled_at,
            tenant_id,
        )

        async def execute():
            handler = self.application.container.get(handler_type)
            parameters = self.registry.parameters(request.definition)
            with self.monitor.span(
                "job.execute",
                {
                    "job.key": declaration.key,
                    "job.id": context.job_id,
                    "job.request_id": context.request_id,
                    "job.attempt": context.attempt,
                },
            ):
                return await self._business(
                    handler, parameters, context, request.definition.timeout_seconds
                )

        try:
            outcome = await self.security.run_workload(
                declaration.source, execute, capability=declaration.capability, tenant_id=tenant_id
            )
        except asyncio.CancelledError as error:
            outcome = JobOutcome(JobState.CANCELLED, error=error)
        except Exception as error:
            outcome = JobOutcome(JobState.FAILED, error=error)
        errors = list(outcome.observation_errors)
        try:
            await AsyncioUtils.run_cancellation_shielded(
                self.record(request, outcome, started, tenant_id)
            )
        except BaseException as error:
            errors.append(error)
        return JobOutcome(outcome.state, outcome.result, outcome.error, tuple(errors))

    async def _business(self, handler, parameters, context, timeout):
        deadline = asyncio.get_running_loop().time() + timeout
        try:
            async with asyncio.timeout_at(deadline):
                execute = await handler.pre_execute(context)
            if type(execute) is not bool:
                raise TypeError("pre_execute 必须返回布尔值")
            if execute is False:
                return JobOutcome(JobState.SKIPPED)
            if inspect.iscoroutinefunction(handler.execute):
                async with asyncio.timeout_at(deadline):
                    result = await handler.execute(parameters, context)
                    await handler.post_execute(result, context)
            else:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError()
                result, interruption = await self._thread(
                    handler.execute, parameters, context, remaining
                )
                if interruption is not None:
                    return JobOutcome(JobState.UNKNOWN, result, error=interruption)
                async with asyncio.timeout_at(deadline):
                    await handler.post_execute(result, context)
            return JobOutcome(JobState.SUCCEEDED, result)
        except asyncio.CancelledError as error:
            return JobOutcome(JobState.CANCELLED, error=error)
        except TimeoutError as error:
            return JobOutcome(JobState.TIMED_OUT, error=error)
        except (AfterCommitException, JobResultUnknown) as error:
            return JobOutcome(JobState.UNKNOWN, error=error)
        except Exception as error:
            try:
                async with asyncio.timeout(self.settings.record_timeout_seconds):
                    state = await handler.on_error(error, context)
                if state not in {JobState.FAILED, JobState.SKIPPED}:
                    raise ValueError("异常钩子只可返回 failed 或 skipped")
                return JobOutcome(state, error=error)
            except Exception as hook_error:
                return JobOutcome(JobState.FAILED, error=error, observation_errors=(hook_error,))

    async def _thread(self, callback, parameters, context, timeout):
        self.running_threads += 1
        task = asyncio.create_task(asyncio.to_thread(callback, parameters, context))
        interruption = None
        try:
            try:
                async with asyncio.timeout(timeout):
                    return await asyncio.shield(task), None
            except (TimeoutError, asyncio.CancelledError) as error:
                interruption = error
                self.timed_out_threads += 1
            # Python 线程无法强杀，直到实际退出才释放 DI/租户上下文及执行名额。
            try:
                value = await AsyncioUtils.run_cancellation_shielded(task)
            except Exception as error:
                value = None
                interruption.add_note(f"线程终态异常：{type(error).__name__}")
            return value, interruption
        finally:
            self.running_threads -= 1
            if interruption is not None:
                self.timed_out_threads -= 1

    async def record(self, request, outcome, started, tenant_id):
        summary = (
            type(outcome.error).__name__
            if outcome.error is not None
            else json.dumps(Sanitizer.sanitize_log_value(outcome.result), ensure_ascii=False)
        )
        record = JobRecord(
            request_id=request.request_id,
            job_id=request.definition.id,
            handler_key=request.definition.handler_key,
            attempt=request.attempt,
            trigger=request.trigger,
            state=outcome.state,
            started_at=started,
            finished_at=datetime.now(UTC),
            tenant_id=tenant_id,
            summary=summary[: self.settings.result_max_length],
        )
        async with asyncio.timeout(self.settings.record_timeout_seconds):
            await self.records.record(record)
