import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import override
from uuid import uuid4

from sqlalchemy import update

from framework.common.dates import DateUtils
from framework.starter_database.public import DatabaseErrorCodes, DatabaseException, SessionProvider
from framework.starter_di.public import Inject, service
from framework.starter_mq.public import (
    MQErrorCodes,
    MQException,
    OutboxProvider,
    OutboxRecord,
    OutboxState,
    PreparedMessage,
    PublishReceipt,
)
from framework.starter_tenant.public import TenantContext
from module_infra.dal.dataobject.mq.mq_outbox_do import MqOutboxDO
from module_infra.dal.mapper.mq.mq_outbox_mapper import MqOutboxMapper


@service(interface=OutboxProvider)
class OutboxProviderAdapter(OutboxProvider):
    """在业务事务内入箱，在租户作用域的独立短事务内认领和结算。"""

    database: SessionProvider = Inject()
    mapper: MqOutboxMapper = Inject()
    tenant: TenantContext = Inject()

    date_utils: DateUtils = Inject()

    def record(self, row: MqOutboxDO) -> OutboxRecord:
        """恢复原始签名消息和发布状态，不重新准备或签名消息。"""
        return OutboxRecord(
            id=row.record_id,
            message=PreparedMessage.model_validate_json(row.message),
            state=OutboxState(row.state),
            attempts=row.attempts,
            created_at=self.date_utils.from_timestamp_micros(row.created_at_us).astimezone(UTC),
            ready_at=self.date_utils.from_timestamp_micros(row.ready_at_us).astimezone(UTC),
            claim_token=row.claim_token,
            claim_expires_at=None
            if row.claim_expires_at_us is None
            else self.date_utils.from_timestamp_micros(row.claim_expires_at_us).astimezone(UTC),
            finished_at=None
            if row.finished_at_us is None
            else self.date_utils.from_timestamp_micros(row.finished_at_us).astimezone(UTC),
            error_type=row.error_type,
        )

    @override
    async def insert(self, record: OutboxRecord) -> None:
        """复用业务事务，重复编号只接受相同的原始消息。"""
        tenant_id = self.tenant.get_required_tenant_id()
        if record.message.envelope.tenant_id != tenant_id:
            raise MQException(MQErrorCodes.AUTHENTICATION)
        message = record.message.model_dump_json()
        async with self.database.transaction():
            try:
                async with self.database.transaction(propagation="nested") as session:
                    session.add(
                        MqOutboxDO(
                            tenant_id=tenant_id,
                            record_id=record.id,
                            message=message,
                            state=record.state.value,
                            attempts=record.attempts,
                            created_at_us=self.date_utils.to_timestamp_micros(record.created_at),
                            ready_at_us=self.date_utils.to_timestamp_micros(record.ready_at),
                            claim_token=record.claim_token,
                            claim_expires_at_us=None
                            if record.claim_expires_at is None
                            else self.date_utils.to_timestamp_micros(record.claim_expires_at),
                            finished_at_us=None
                            if record.finished_at is None
                            else self.date_utils.to_timestamp_micros(record.finished_at),
                            error_type=record.error_type,
                        )
                    )
                    await session.flush()
            except DatabaseException as error:
                if error.error_code is not DatabaseErrorCodes.UNIQUE_VIOLATION:
                    raise
                current = await self.mapper.select_record(record.id)
                if current is None:
                    raise
                if current.message != message:
                    raise MQException(MQErrorCodes.CONFLICT) from None

    @override
    async def claim(
        self, *, now: datetime, lease_seconds: float, max_attempts: int, record_id: str | None
    ) -> OutboxRecord | None:
        """提交独占随机租约后才返回消息，过期在途记录不再认领。"""
        tenant_id = self.tenant.get_required_tenant_id()
        now_us = self.date_utils.to_timestamp_micros(now)
        async with self.database.transaction(propagation="requires_new"):
            await self.mapper.expire(tenant_id, now_us, max_attempts)
            row = await self.mapper.select_ready(now_us, record_id)
            if row is None:
                return None
            claimed = self.record(row).model_copy(
                update={
                    "state": OutboxState.SENDING,
                    "attempts": row.attempts + 1,
                    "claim_token": uuid4().hex,
                    "claim_expires_at": now + timedelta(seconds=lease_seconds),
                }
            )
            await self.mapper.update_by_condition(
                {
                    "state": claimed.state.value,
                    "attempts": claimed.attempts,
                    "claim_token": claimed.claim_token,
                    "claim_expires_at_us": self.date_utils.to_timestamp_micros(
                        claimed.claim_expires_at
                    ),
                },
                MqOutboxDO.id == row.id,
            )
            return claimed

    @override
    async def finish(
        self,
        record: OutboxRecord,
        *,
        state: OutboxState,
        ready_at: datetime,
        error_type: str | None,
        receipt: PublishReceipt | None,
    ) -> None:
        """按令牌、在途状态和未过期租约结算，同一成功回执可重试。"""
        tenant_id = self.tenant.get_required_tenant_id()
        if state not in {
            OutboxState.PENDING,
            OutboxState.PUBLISHED,
            OutboxState.DEAD,
            OutboxState.UNKNOWN,
        }:
            raise MQException(MQErrorCodes.INVALID)
        receipt_text = (
            None
            if receipt is None
            else json.dumps(asdict(receipt), ensure_ascii=False, sort_keys=True)
        )
        async with self.database.transaction(propagation="requires_new"):
            current = await self.mapper.select_record(record.id)
            if (
                current is not None
                and state is OutboxState.PUBLISHED
                and current.state == state.value
                and current.settled_token == record.claim_token
                and current.receipt == receipt_text
            ):
                return
            now_us = self.date_utils.to_timestamp_micros(datetime.now(UTC))
            result = await self.mapper.write(
                update(MqOutboxDO)
                .where(
                    MqOutboxDO.tenant_id == tenant_id,
                    MqOutboxDO.record_id == record.id,
                    MqOutboxDO.state == OutboxState.SENDING.value,
                    MqOutboxDO.claim_token == record.claim_token,
                    MqOutboxDO.claim_expires_at_us > now_us,
                )
                .values(
                    state=state.value,
                    ready_at_us=self.date_utils.to_timestamp_micros(ready_at),
                    claim_token=None,
                    claim_expires_at_us=None,
                    finished_at_us=now_us
                    if state in {OutboxState.PUBLISHED, OutboxState.DEAD}
                    else None,
                    error_type=error_type,
                    settled_token=record.claim_token,
                    receipt=receipt_text,
                )
            )
            if result.rowcount != 1:
                raise MQException(MQErrorCodes.LEASE)

    @override
    async def cancel(self, record_id: str) -> bool:
        """仅取消尚未发布的当前租户记录。"""
        tenant_id = self.tenant.get_required_tenant_id()
        async with self.database.transaction(propagation="requires_new"):
            result = await self.mapper.write(
                update(MqOutboxDO)
                .where(
                    MqOutboxDO.tenant_id == tenant_id,
                    MqOutboxDO.record_id == record_id,
                    MqOutboxDO.state == OutboxState.PENDING.value,
                )
                .values(
                    state=OutboxState.CANCELLED.value,
                    finished_at_us=self.date_utils.to_timestamp_micros(datetime.now(UTC)),
                )
            )
            return result.rowcount == 1

    @override
    async def cleanup(self, *, before: datetime, limit: int) -> int:
        """有界清理保留期外的确定终态，未知结果保留人工核定。"""
        self.tenant.get_required_tenant_id()
        async with self.database.transaction(propagation="requires_new"):
            return await self.mapper.purge_limited_by_condition(
                MqOutboxDO.state.in_(
                    (
                        OutboxState.PUBLISHED.value,
                        OutboxState.DEAD.value,
                        OutboxState.CANCELLED.value,
                    )
                ),
                MqOutboxDO.finished_at_us < self.date_utils.to_timestamp_micros(before),
                limit=limit,
            )
