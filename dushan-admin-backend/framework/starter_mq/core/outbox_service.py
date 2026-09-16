import asyncio
import hashlib
from datetime import UTC, datetime, timedelta

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.starter_di.decorators.components import framework
from framework.starter_mq.core.mq_service import MQService
from framework.starter_mq.enums.outbox_state import OutboxState
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.outbox_record import OutboxRecord


@framework
class OutboxService:
    """同事务入箱、提交后尝试发布、Job 补扫；UNKNOWN 必须由业务核定。"""

    def __init__(self, mq: MQService):
        self.mq = mq

    def _resources(self):
        runtime = self.mq.require_runtime()
        if (
            not runtime.settings.outbox_enabled
            or runtime.outbox is None
            or runtime.database is None
        ):
            raise MQException("configuration")
        return runtime, runtime.outbox

    async def enqueue(self, command) -> str:
        runtime, provider = self._resources()
        message = await self.mq.prepare(command)
        envelope = message.envelope
        record_id = hashlib.sha256(
            runtime.codec.canonical([envelope.tenant_id, envelope.destination, envelope.message_id])
        ).hexdigest()
        now = datetime.now(UTC)
        record = OutboxRecord(
            id=record_id,
            message=message,
            state=OutboxState.PENDING,
            attempts=0,
            created_at=now,
            ready_at=now,
            claim_token=None,
            claim_expires_at=None,
            finished_at=None,
            error_type=None,
        )
        async with runtime.database.transaction():
            await provider.insert(record)
            runtime.database.after_commit(
                lambda: self.dispatch(record_id=record_id), required=True, name="mq-outbox-publish"
            )
        return record_id

    async def dispatch(self, *, record_id=None, limit=None):
        runtime, provider = self._resources()
        settings = runtime.settings
        selected_limit = settings.outbox_batch_size if limit is None else limit
        if not 1 <= selected_limit <= settings.outbox_batch_size:
            raise MQException("invalid")
        counts = {state.value: 0 for state in OutboxState}
        for _ in range(1 if record_id is not None else selected_limit):
            # 逐条认领，避免一个批次尾部在轮到发布前租约就已过期。
            record = await runtime.call(
                provider.claim(
                    now=datetime.now(UTC),
                    lease_seconds=settings.outbox_lease_seconds,
                    max_attempts=settings.outbox_max_attempts,
                    record_id=record_id,
                )
            )
            if record is None:
                break
            if (
                record.state is not OutboxState.SENDING
                or record.claim_expires_at is None
                or record.claim_expires_at <= datetime.now(UTC)
            ):
                raise MQException("lease")
            receipt = None
            error = None
            state = OutboxState.PUBLISHED
            try:
                receipt = await self.mq.send_prepared(record.message)
            except asyncio.CancelledError as cancellation:
                await AsyncioUtils.run_cancellation_shielded(
                    runtime.call(
                        provider.finish(
                            record,
                            state=OutboxState.UNKNOWN,
                            ready_at=datetime.now(UTC),
                            error_type=type(cancellation).__name__,
                            receipt=None,
                        )
                    ),
                    propagate_cancellation=False,
                )
                raise
            except MQException as failure:
                error = failure
                if failure.reason == "unknown":
                    state = OutboxState.UNKNOWN
                elif (
                    failure.reason in {"capacity", "closed", "confirmation"}
                    and record.attempts < settings.outbox_max_attempts
                ):
                    state = OutboxState.PENDING
                else:
                    state = OutboxState.DEAD
            except Exception as failure:
                error, state = failure, OutboxState.UNKNOWN
            ready = datetime.now(UTC) + timedelta(
                seconds=min(
                    settings.max_retry_delay_seconds,
                    settings.outbox_retry_seconds * 2 ** min(record.attempts - 1, 32),
                )
            )
            await AsyncioUtils.run_cancellation_shielded(
                runtime.call(
                    provider.finish(
                        record,
                        state=state,
                        ready_at=ready,
                        error_type=type(error).__name__ if error else None,
                        receipt=receipt,
                    )
                ),
                propagate_cancellation=False,
            )
            counts[state.value] += 1
            if record_id is not None and error is not None:
                # Database 将其报告为提交后失败，已提交事实保持不变。
                raise error
        return counts

    async def cleanup(self):
        runtime, provider = self._resources()
        return await runtime.call(
            provider.cleanup(
                before=datetime.now(UTC)
                - timedelta(seconds=runtime.settings.outbox_retention_seconds),
                limit=runtime.settings.outbox_batch_size,
            )
        )
