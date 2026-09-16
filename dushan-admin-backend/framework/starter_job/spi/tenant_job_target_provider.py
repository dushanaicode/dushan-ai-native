from typing import Protocol

from framework.starter_job.model.tenant_job_lease import TenantJobLease


class TenantJobTargetProvider(Protocol):
    """每租户目标单独认领/结算；已完成跳过，过期在途结果未知不能自动重放。"""

    async def claim(
        self, request_id: str, tenant_id: str, lease_seconds: float
    ) -> TenantJobLease | None: ...
    async def complete(self, lease: TenantJobLease) -> None: ...
    async def release(self, lease: TenantJobLease) -> None: ...
