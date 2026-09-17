import json
from datetime import timezone

from sqlalchemy import func, select, update

from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_job.enums.job_trigger_kind import JobTriggerKind
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.model.job_request import JobRequest
from module_infra.dal.dataobject.job.job_request_do import JobRequestDO
from module_infra.dal.dataobject.job.job_schedule_do import JobScheduleDO
from module_infra.dal.dataobject.job.job_signal_do import JobSignalDO


@service
class JobRequestStore:
    database: SessionProvider = Inject()

    def __init__(self):
        self.seen_revision = -1

    @staticmethod
    def utc(value):
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    async def submit(self, request, *, pending_limit):
        async with self.database.transaction() as session:
            await session.execute(select(JobSignalDO).where(JobSignalDO.id == 1).with_for_update())
            if (
                await session.scalar(
                    select(JobRequestDO.id).where(JobRequestDO.request_id == request.request_id)
                )
                is not None
            ):
                return False
            checkpoint = None
            if request.trigger is JobTriggerKind.SCHEDULED:
                checkpoint = (
                    await session.execute(
                        select(JobScheduleDO)
                        .where(JobScheduleDO.job_id == int(request.definition.id))
                        .with_for_update()
                    )
                ).scalar_one_or_none()
                if (
                    checkpoint is not None
                    and self.utc(request.scheduled_at) <= checkpoint.checkpoint
                ):
                    return False
            pending = await session.scalar(
                select(func.count())
                .select_from(JobRequestDO)
                .where(JobRequestDO.state.in_(("pending", "claimed")))
            )
            if pending >= pending_limit:
                raise JobException("capacity")
            session.add(
                JobRequestDO(
                    request_id=request.request_id,
                    job_id=int(request.definition.id),
                    request=request.model_dump(mode="json", by_alias=False),
                    state="pending",
                    ready_at=self.utc(request.ready_at),
                )
            )
            if request.trigger is JobTriggerKind.SCHEDULED:
                if checkpoint is None:
                    session.add(
                        JobScheduleDO(
                            job_id=int(request.definition.id),
                            checkpoint=self.utc(request.scheduled_at),
                        )
                    )
                else:
                    checkpoint.checkpoint = self.utc(request.scheduled_at)
            await session.flush()
        return True

    async def checkpoint(self, job_id):
        async with self.database.read_session(force_primary=True) as session:
            value = await session.scalar(
                select(JobScheduleDO.checkpoint).where(JobScheduleDO.job_id == int(job_id))
            )
        return None if value is None else value.replace(tzinfo=timezone.utc)

    async def claim(self, owner, *, exclude_jobs, now):
        async with self.database.transaction() as session:
            await session.execute(
                update(JobRequestDO)
                .where(JobRequestDO.state == "claimed", JobRequestDO.owner != owner)
                .values(state="unknown")
            )
            query = select(JobRequestDO).where(
                JobRequestDO.state == "pending", JobRequestDO.ready_at <= self.utc(now)
            )
            if exclude_jobs:
                query = query.where(
                    JobRequestDO.job_id.not_in([int(value) for value in exclude_jobs])
                )
            row = (
                await session.execute(
                    query.order_by(JobRequestDO.ready_at, JobRequestDO.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            row.state, row.owner = ("claimed", owner)
            await session.flush()
            return JobRequest.model_validate_json(json.dumps(row.request))

    async def finish(self, request_id, owner, state):
        async with self.database.transaction() as session:
            result = await session.execute(
                update(JobRequestDO)
                .where(
                    JobRequestDO.request_id == request_id,
                    JobRequestDO.owner == owner,
                    JobRequestDO.state == "claimed",
                )
                .values(state=state.code)
            )
            if result.rowcount != 1:
                raise JobException("owner")

    async def retry(self, request, owner):
        async with self.database.transaction() as session:
            result = await session.execute(
                update(JobRequestDO)
                .where(
                    JobRequestDO.request_id == request.request_id,
                    JobRequestDO.owner == owner,
                    JobRequestDO.state == "claimed",
                )
                .values(
                    state="pending",
                    owner=None,
                    request=request.model_dump(mode="json", by_alias=False),
                    ready_at=self.utc(request.ready_at),
                )
            )
            if result.rowcount != 1:
                raise JobException("owner")

    async def notify_changed(self):
        async with self.database.transaction() as session:
            result = await session.execute(
                update(JobSignalDO)
                .where(JobSignalDO.id == 1)
                .values(revision=JobSignalDO.revision + 1)
            )
            if result.rowcount != 1:
                raise JobException("configuration")

    async def consume_changes(self):
        async with self.database.read_session(force_primary=True) as session:
            revision = (
                await session.execute(select(JobSignalDO.revision).where(JobSignalDO.id == 1))
            ).scalar_one()
        changed = revision != self.seen_revision
        self.seen_revision = revision
        return changed
