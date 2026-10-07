from sqlalchemy import select, update

from framework.starter_database.public import BaseMapper
from framework.starter_di.public import mapper
from framework.starter_mq.public import OutboxState
from module_infra.dal.dataobject.mq.mq_outbox_do import MqOutboxDO


@mapper()
class MqOutboxMapper(BaseMapper[MqOutboxDO]):
    def __init__(self):
        super().__init__(MqOutboxDO)

    async def select_record(self, record_id: str) -> MqOutboxDO | None:
        """锁定当前租户的记录，锁由调用方事务持有。"""
        result = await self.execute(
            select(MqOutboxDO).where(MqOutboxDO.record_id == record_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def select_ready(
        self, now_us: int, record_id: str | None, max_attempts: int
    ) -> MqOutboxDO | None:
        """按到期顺序读取当前租户候选，独占认领由条件 UPDATE 决定。"""
        query = select(MqOutboxDO).where(
            MqOutboxDO.state == OutboxState.PENDING.value,
            MqOutboxDO.ready_at_us <= now_us,
            MqOutboxDO.attempts < max_attempts,
            MqOutboxDO.claim_token.is_(None),
            MqOutboxDO.claim_expires_at_us.is_(None),
        )
        if record_id is not None:
            query = query.where(MqOutboxDO.record_id == record_id)
        result = await self.execute(query.order_by(MqOutboxDO.ready_at_us, MqOutboxDO.id).limit(1))
        return result.scalar_one_or_none()

    async def expire(self, tenant_id: str, now_us: int, max_attempts: int) -> None:
        """先读到期编号，再按主键更新，避免范围锁与并发认领形成死锁。"""
        for conditions, values in (
            (
                (
                    MqOutboxDO.tenant_id == tenant_id,
                    MqOutboxDO.state == OutboxState.SENDING.value,
                    MqOutboxDO.claim_expires_at_us <= now_us,
                ),
                dict(state=OutboxState.UNKNOWN.value, claim_token=None, claim_expires_at_us=None),
            ),
            (
                (
                    MqOutboxDO.tenant_id == tenant_id,
                    MqOutboxDO.state == OutboxState.PENDING.value,
                    MqOutboxDO.ready_at_us <= now_us,
                    MqOutboxDO.attempts >= max_attempts,
                ),
                dict(state=OutboxState.DEAD.value, finished_at_us=now_us),
            ),
        ):
            result = await self.read(
                select(MqOutboxDO.id).where(*conditions).order_by(MqOutboxDO.id)
            )
            for identifier in result.scalars():
                # 更新时重验租户、状态和时间，保留并发结算或续租后的记录。
                await self.write(
                    update(MqOutboxDO)
                    .where(MqOutboxDO.id == identifier, *conditions)
                    .values(**values)
                )
