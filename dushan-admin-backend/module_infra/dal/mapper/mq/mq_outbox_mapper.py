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

    async def select_ready(self, now_us: int, record_id: str | None) -> MqOutboxDO | None:
        """按到期顺序独占认领一条待发布记录。"""
        query = select(MqOutboxDO).where(
            MqOutboxDO.state == OutboxState.PENDING.value, MqOutboxDO.ready_at_us <= now_us
        )
        if record_id is not None:
            query = query.where(MqOutboxDO.record_id == record_id)
        result = await self.execute(
            query.order_by(MqOutboxDO.ready_at_us, MqOutboxDO.id).limit(1).with_for_update()
        )
        return result.scalar_one_or_none()

    async def expire(self, tenant_id: str, now_us: int, max_attempts: int) -> None:
        """隔离失联发布，终止超过次数上限的到期记录。"""
        await self.write(
            update(MqOutboxDO)
            .where(
                MqOutboxDO.tenant_id == tenant_id,
                MqOutboxDO.state == OutboxState.SENDING.value,
                MqOutboxDO.claim_expires_at_us <= now_us,
            )
            .values(state=OutboxState.UNKNOWN.value, claim_token=None, claim_expires_at_us=None)
        )
        await self.write(
            update(MqOutboxDO)
            .where(
                MqOutboxDO.tenant_id == tenant_id,
                MqOutboxDO.state == OutboxState.PENDING.value,
                MqOutboxDO.ready_at_us <= now_us,
                MqOutboxDO.attempts >= max_attempts,
            )
            .values(state=OutboxState.DEAD.value, finished_at_us=now_us)
        )
