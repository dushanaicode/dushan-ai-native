import asyncio
import hashlib
from collections import Counter
from contextvars import Context
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apscheduler.events import EVENT_SCHEDULER_SHUTDOWN
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from framework.starter_cache.lock.redis_lease_lock import RedisLeaseLock
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_job.core.job_invoker import JobInvoker
from framework.starter_job.core.tenant_job_runner import TenantJobRunner
from framework.starter_job.cron.standard_cron_trigger import StandardCronTrigger
from framework.starter_job.enums.job_state import JobState
from framework.starter_job.enums.job_trigger_kind import JobTriggerKind
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.model.job_definition import JobDefinition
from framework.starter_job.model.job_outcome import JobOutcome
from framework.starter_job.model.job_request import JobRequest


class JobRuntime:
    """内存调度副本、单 owner 信箱和有界执行；业务定义始终由 SPI 提供。"""

    def __init__(
        self,
        settings,
        application,
        registry,
        definitions,
        requests,
        records,
        security,
        cache,
        tenant,
        tenant_targets,
        monitor,
    ):
        self.settings, self.application, self.registry = settings, application, registry
        self.definitions, self.requests, self.cache = definitions, requests, cache
        self.invoker = JobInvoker(application, security, registry, records, settings, monitor)
        self.tenant_runner = TenantJobRunner(
            tenant, tenant_targets, self.invoker, settings.tenant_lease_seconds
        )
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone=registry.timezone,
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": None},
        )
        self.plans = {}
        self.running = {}
        self.counts = Counter()
        self.lease = None
        self.owner = False
        self.accepting = False
        self.phase = "new"
        self.failure = None
        self.observation_failures = 0
        self._stop = asyncio.Event()
        self._renew_stop = asyncio.Event()
        self._loop_task = None
        self._renew_task = None
        self._closing = None
        self._sync_lock = asyncio.Lock()

    async def _call(self, callback):
        async with asyncio.timeout(self.settings.command_timeout_seconds):
            return await callback()

    async def open(self):
        if any(
            value is None
            for value in (
                self.definitions,
                self.requests,
                self.invoker.records,
                self.invoker.security,
            )
        ):
            raise JobException("configuration")
        self.phase = "starting"
        self.accepting = True
        if self.settings.owner_enabled:
            key = self.settings.owner_key()
            self.lease = RedisLeaseLock(
                self.cache.get_client(key),
                self.cache.build_full_key(key, self.settings.namespace),
                self.settings.owner_lease_seconds,
                0,
                command_timeout_seconds=self.settings.command_timeout_seconds,
            )
            self.owner = await self.lease.acquire()
            if self.owner:
                self.scheduler.start(paused=True)
                self._renew_task = asyncio.create_task(
                    self._renew(), context=Context(), name="job-owner-renew"
                )
                await self.reconcile()
        self.phase = "waiting" if self.owner else "client"
        self._loop_task = asyncio.create_task(
            self._loop(), context=Context(), name="job-owner-loop"
        )

    def _require_owner(self):
        if not self.owner or self.lease is None or not self.lease.is_valid:
            raise JobException("owner")

    def _lose_owner(self, error=None):
        self.owner = False
        self.phase = "owner_lost"
        self.failure = error
        if self.scheduler.running:
            self.scheduler.pause()

    async def _renew(self):
        while not self._renew_stop.is_set():
            try:
                await asyncio.wait_for(self._renew_stop.wait(), self.settings.owner_renew_seconds)
                return
            except TimeoutError:
                pass
            try:
                if not await self.lease.renew():
                    self._lose_owner()
                    return
            except Exception as error:
                self._lose_owner(error)
                logger.error("Job owner 续租失败，停止新触发：{}", type(error).__name__)
                return

    async def reconcile(self):
        self._require_owner()
        async with self._sync_lock:
            try:
                definitions = await self._call(self.definitions.list_definitions)
                if (
                    not isinstance(definitions, tuple)
                    or len(definitions) > self.settings.max_jobs
                    or any(not isinstance(item, JobDefinition) for item in definitions)
                ):
                    raise JobException("configuration")
            except Exception:
                self.scheduler.remove_all_jobs()
                self.plans.clear()
                raise
            incoming = {}
            seen = set()
            errors = []
            for definition in definitions:
                if definition.id in seen:
                    self.scheduler.remove_all_jobs()
                    self.plans.clear()
                    raise JobException("configuration")
                seen.add(definition.id)
                if not definition.enabled:
                    continue
                try:
                    schedule = self.registry.validate(definition)
                    if definition.fan_out and (
                        self.tenant_runner.targets is None
                        or self.tenant_runner.tenant is None
                        or not self.tenant_runner.tenant.ready
                    ):
                        raise JobException("configuration")
                    incoming[definition.id] = definition.model_copy(deep=True)
                    if self.plans.get(definition.id) != definition:
                        self.scheduler.add_job(
                            self._scheduled,
                            trigger=StandardCronTrigger(schedule),
                            args=(definition.id,),
                            id=definition.id,
                            replace_existing=True,
                        )
                    await self._submit_latest(definition, schedule)
                except Exception as error:
                    incoming.pop(definition.id, None)
                    if self.scheduler.get_job(definition.id) is not None:
                        self.scheduler.remove_job(definition.id)
                    errors.append(error)
            for job in self.scheduler.get_jobs():
                if job.id not in incoming:
                    self.scheduler.remove_job(job.id)
            self.plans = incoming
            if errors:
                raise ExceptionGroup("任务同步失败；相关计划已移除", errors)

    async def _submit_latest(self, definition, schedule):
        now = datetime.now(UTC)
        due = schedule.previous(now)
        checkpoint = await self._call(lambda: self.requests.checkpoint(definition.id))
        if due < definition.effective_at or checkpoint is not None and due <= checkpoint:
            return
        identity = hashlib.sha256(
            f"{definition.id}:{definition.revision}:{due.isoformat()}".encode()
        ).hexdigest()
        request = JobRequest(
            request_id=identity,
            definition=definition.model_copy(deep=True),
            trigger=JobTriggerKind.SCHEDULED,
            scheduled_at=due,
            ready_at=now,
            attempt=1,
        )
        await self._call(
            lambda: self.requests.submit(request, pending_limit=self.settings.pending_limit)
        )

    async def _scheduled(self, job_id):
        if not self.owner or self.application.state is not ApplicationStateEnum.READY:
            return
        self._require_owner()
        with self.application.execution():
            definition = self.plans.get(job_id)
            if definition is not None:
                await self._submit_latest(definition, self.registry.validate(definition))

    async def submit_manual(self, job_id):
        if not self.accepting:
            raise JobException("closed")
        definition = await self._call(lambda: self.definitions.get_definition(job_id))
        if definition is None or not definition.enabled:
            raise JobException("disabled")
        self.registry.validate(definition)
        now = datetime.now(UTC)
        request = JobRequest(
            request_id=uuid4().hex,
            definition=definition.model_copy(deep=True),
            trigger=JobTriggerKind.MANUAL,
            scheduled_at=now,
            ready_at=now,
            attempt=1,
        )
        await self._call(
            lambda: self.requests.submit(request, pending_limit=self.settings.pending_limit)
        )
        return request.request_id

    async def _loop(self):
        await self.application.wait_until_ready()
        if self.owner:
            self.scheduler.resume()
            self.phase = "running"
        next_sync = asyncio.get_running_loop().time() + self.settings.reconciliation_seconds
        while not self._stop.is_set() and self.application.state is ApplicationStateEnum.READY:
            if self.owner and not self.lease.is_valid:
                self._lose_owner()
            if self.owner:
                try:
                    with self.application.execution():
                        if (
                            await self._call(self.requests.consume_changes)
                            or asyncio.get_running_loop().time() >= next_sync
                        ):
                            try:
                                await self.reconcile()
                            except Exception as error:
                                self.failure = error
                                logger.error(
                                    "Job 周期同步失败，已按任务 fail-closed：{}",
                                    type(error).__name__,
                                )
                            next_sync = (
                                asyncio.get_running_loop().time()
                                + self.settings.reconciliation_seconds
                            )
                        await self._dispatch()
                except Exception as error:
                    self.failure = error
                    self.phase = "failed"
                    self._lose_owner(error)
                    logger.error("Job owner 控制循环失败，停止新执行：{}", type(error).__name__)
                    break
            try:
                await asyncio.wait_for(self._stop.wait(), self.settings.poll_seconds)
            except TimeoutError:
                pass

    async def _dispatch(self):
        while len(self.running) < self.settings.concurrency:
            self._require_owner()
            excluded = frozenset(
                job_id
                for job_id, count in self.counts.items()
                if job_id not in self.plans or count >= self.plans[job_id].max_instances
            )
            request = await self._call(
                lambda: self.requests.claim(
                    self.lease.owner_token, exclude_jobs=excluded, now=datetime.now(UTC)
                )
            )
            if request is None:
                return
            if (
                not self.owner
                or not self.lease.is_valid
                or self.application.state is not ApplicationStateEnum.READY
            ):
                await self._call(lambda: self.requests.retry(request, self.lease.owner_token))
                self._lose_owner()
                return
            job_id = request.definition.id
            if self.counts[job_id] >= request.definition.max_instances:
                await self._call(lambda: self.requests.retry(request, self.lease.owner_token))
                return
            self.counts[job_id] += 1
            task = self.application.tasks.create_task(
                self._execute_request, request, name="job-" + request.request_id
            )
            self.running[request.request_id] = (job_id, task)
            task.add_done_callback(
                lambda completed, identifier=request.request_id: self._completed(
                    identifier, completed
                )
            )

    def _completed(self, request_id, task):
        job_id, _ = self.running.pop(request_id)
        self.counts[job_id] -= 1
        if not self.counts[job_id]:
            del self.counts[job_id]
        if not task.cancelled() and task.exception() is not None:
            self._lose_owner(task.exception())

    async def _execute_request(self, request):
        if not self.owner or not self.lease.is_valid:
            await self._call(lambda: self.requests.retry(request, self.lease.owner_token))
            return
        current = await self._call(lambda: self.definitions.get_definition(request.definition.id))
        started = datetime.now(UTC)
        if current is None or not current.enabled or current != request.definition:
            outcome = JobOutcome(JobState.SKIPPED, error=JobException("snapshot"))
            await self._record_only(request, outcome, started)
        elif (
            request.trigger is JobTriggerKind.SCHEDULED
            and request.attempt == 1
            and started - request.scheduled_at
            > timedelta(seconds=self.settings.misfire_grace_seconds)
        ):
            outcome = JobOutcome(JobState.SKIPPED, result="misfire_grace_exceeded")
            await self._record_only(request, outcome, started)
        else:
            self.registry.validate(current)
            outcome = (
                await self.tenant_runner.run(request)
                if current.fan_out
                else await self.invoker.invoke(request, current.tenant_id)
            )
        self.observation_failures += len(outcome.observation_errors)
        if (
            outcome.state is JobState.FAILED
            and request.attempt <= request.definition.max_retries
            and self.owner
            and self.accepting
        ):
            delay = min(
                self.settings.max_retry_seconds,
                request.definition.retry_seconds
                * request.definition.retry_backoff ** (request.attempt - 1),
            )
            retry = request.model_copy(
                update={
                    "attempt": request.attempt + 1,
                    "ready_at": datetime.now(UTC) + timedelta(seconds=delay),
                }
            )
            await self._call(lambda: self.requests.retry(retry, self.lease.owner_token))
            return
        await self._call(
            lambda: self.requests.finish(request.request_id, self.lease.owner_token, outcome.state)
        )
        if (
            outcome.state in {JobState.FAILED, JobState.TIMED_OUT, JobState.UNKNOWN}
            and request.definition.stop_after_failure
        ):
            await self._call(
                lambda: self.definitions.stop_definition(
                    request.definition.id, request.definition.revision
                )
            )
            if self.scheduler.get_job(request.definition.id) is not None:
                self.scheduler.remove_job(request.definition.id)

    async def _record_only(self, request, outcome, started):
        try:
            await self.invoker.record(request, outcome, started, request.definition.tenant_id)
        except Exception as error:
            self.observation_failures += 1
            logger.error("Job 观测失败，业务终态保持：{}", type(error).__name__)

    async def close(self):
        if self._closing is None:
            self._closing = asyncio.create_task(self._close(), name="job-close")
        await asyncio.shield(self._closing)

    async def _close(self):
        self.accepting = False
        self.phase = "closing"
        if self.scheduler.running:
            self.scheduler.pause()
        self._stop.set()
        if self._loop_task is not None and self.application.state is ApplicationStateEnum.STARTING:
            self._loop_task.cancel()
        tasks = [task for task in (self._loop_task,) if task is not None]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        running = [task for _, task in self.running.values()]
        if running:
            _, pending = await asyncio.wait(running, timeout=self.settings.shutdown_seconds)
            for task in pending:
                task.cancel()
            await asyncio.gather(*running, return_exceptions=True)
        self._renew_stop.set()
        if self._renew_task is not None:
            await self._renew_task
        if self.lease is not None and self.lease.release_required:
            await self.lease.release()
        if self.scheduler.running:
            closed = asyncio.Event()
            self.scheduler.add_listener(lambda event: closed.set(), EVENT_SCHEDULER_SHUTDOWN)
            self.scheduler.shutdown(wait=False)
            await closed.wait()
        self.owner = False
        self.phase = "closed"

    def status(self):
        return {
            "phase": self.phase,
            "owner": self.owner and self.lease is not None and self.lease.is_valid,
            "plans": len(self.plans),
            "running": len(self.running),
            "running_threads": self.invoker.running_threads,
            "timed_out_threads": self.invoker.timed_out_threads,
            "observation_failures": self.observation_failures,
            "failure": None if self.failure is None else type(self.failure).__name__,
        }
