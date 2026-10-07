from datetime import UTC, datetime, timedelta
from typing import override
from uuid import uuid4

from framework.common.dates import DateUtils
from framework.starter_di.public import Inject, service
from framework.starter_job.public import TenantJobLease, TenantJobTargetProvider
from module_infra.dal.dataobject.job.tenant_job_target_do import TenantJobTargetDO
from module_infra.dal.mapper.job.tenant_job_target_mapper import TenantJobTargetMapper


@service(interface=TenantJobTargetProvider)
class TenantJobTargetProviderAdapter(TenantJobTargetProvider):
    mapper: TenantJobTargetMapper = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def claim(
        self, request_id: str, tenant_id: str, lease_seconds: float
    ) -> TenantJobLease | None:
        """持久认领单个租户，事务提交后才返回租约。"""
        now = datetime.now(UTC)
        lease = TenantJobLease(
            request_id=request_id,
            tenant_id=tenant_id,
            token=uuid4().hex,
            expires_at=now + timedelta(seconds=lease_seconds),
        )
        claimed = await self.mapper.claim(
            TenantJobTargetDO(
                request_id=request_id,
                tenant_id=tenant_id,
                token=lease.token,
                expires_at_us=self.date_utils.to_timestamp_micros(lease.expires_at),
                state="claimed",
            ),
            self.date_utils.to_timestamp_micros(now),
        )
        return lease if claimed else None

    @override
    async def complete(self, lease: TenantJobLease) -> None:
        """保存确定完成结果，使同一请求的此租户永久跳过。"""
        await self._settle(lease, "completed")

    @override
    async def release(self, lease: TenantJobLease) -> None:
        """释放仍有效且已明确失败的认领，供同一请求重试。"""
        await self._settle(lease, "pending")

    async def _settle(self, lease: TenantJobLease, state: str) -> None:
        """将完整租约和目标状态交给持久化层核对。"""
        await self.mapper.settle(
            lease.request_id,
            lease.tenant_id,
            lease.token,
            self.date_utils.to_timestamp_micros(lease.expires_at),
            state,
            self.date_utils.to_timestamp_micros(datetime.now(UTC)),
        )
