from datetime import datetime

from sqlalchemy import select, update

from framework.starter_database.public import BaseMapper
from framework.starter_di.public import mapper
from framework.starter_job.public import JobErrorCodes, JobException, JobState
from module_infra.dal.dataobject.job.job_request_do import JobRequestDO
from module_infra.dal.dataobject.job.tenant_job_target_do import TenantJobTargetDO


@mapper()
class TenantJobTargetMapper(BaseMapper[TenantJobTargetDO]):
    def __init__(self):
        super().__init__(TenantJobTargetDO)

    async def claim(self, target: TenantJobTargetDO, now_us: int) -> bool:
        """以请求行锁串行化首次插入；过期认领转为未知，禁止自动重放。"""
        async with self.session_provider.transaction(propagation="requires_new") as session:
            parent_state = (
                await session.execute(
                    select(JobRequestDO.state)
                    .where(JobRequestDO.request_id == target.request_id)
                    .with_for_update()
                )
            ).scalar_one()
            # 父请求终结后即使台账已清理，也不能重新认领并执行。
            if parent_state != "claimed":
                return False
            current = await session.scalar(
                select(TenantJobTargetDO)
                .where(
                    TenantJobTargetDO.request_id == target.request_id,
                    TenantJobTargetDO.tenant_id == target.tenant_id,
                )
                .with_for_update()
            )
            if current is None:
                session.add(target)
            elif current.state == "pending":
                current.state = target.state
                current.token = target.token
                current.expires_at_us = target.expires_at_us
            else:
                if current.state == "claimed" and current.expires_at_us <= now_us:
                    current.state = "unknown"
                return False
            await session.flush()
            return True

    async def delete_finished_before(self, before: datetime, limit: int) -> int:
        """有界清理已终结请求的台账；保留未知结果、在途认领和父请求防重放记录。"""
        finished_requests = select(JobRequestDO.request_id).where(
            JobRequestDO.state.in_(
                tuple(state.code for state in JobState if state is not JobState.UNKNOWN)
            ),
            JobRequestDO.update_time < before,
        )
        return await self.purge_limited_by_condition(
            TenantJobTargetDO.request_id.in_(finished_requests),
            TenantJobTargetDO.state.in_(("pending", "completed")),
            TenantJobTargetDO.update_time < before,
            limit=limit,
        )

    async def settle(
        self,
        request_id: str,
        tenant_id: str,
        token: str,
        expires_at_us: int,
        state: str,
        now_us: int,
    ) -> None:
        """按完整租约 CAS 结算；仅有效认领可释放，未知结果只能补记确定完成。"""
        query = update(TenantJobTargetDO).where(
            TenantJobTargetDO.request_id == request_id,
            TenantJobTargetDO.tenant_id == tenant_id,
            TenantJobTargetDO.token == token,
            TenantJobTargetDO.expires_at_us == expires_at_us,
        )
        if state == "pending":
            query = query.where(
                TenantJobTargetDO.state == "claimed", TenantJobTargetDO.expires_at_us > now_us
            )
        else:
            query = query.where(TenantJobTargetDO.state.in_(("claimed", "unknown")))
        async with self.session_provider.transaction(propagation="requires_new") as session:
            result = await session.execute(query.values(state=state))
            if result.rowcount != 1:
                raise JobException(JobErrorCodes.OWNER)
