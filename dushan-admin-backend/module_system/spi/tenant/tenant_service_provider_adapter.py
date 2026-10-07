from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import LoginSession, WorkloadIdentity
from framework.starter_tenant.public import (
    TenantAccessGrant,
    TenantDirectoryProvider,
    TenantInfo,
)
from framework.starter_web.public import RoutePolicy
from module_system.service.tenant.tenant_service import TenantService


@service(interface=TenantDirectoryProvider)
class TenantServiceProviderAdapter(TenantDirectoryProvider):
    delegate: TenantService = Inject()

    @override
    async def get_tenant(self, tenant_id: str) -> TenantInfo | None:
        return await self.delegate.tenant_info(tenant_id)

    @override
    async def authorize_session(
        self, identity: LoginSession, policy: RoutePolicy
    ) -> TenantAccessGrant | None:
        return await self.delegate.authorize_session(identity, policy)

    @override
    async def authorize_workload(
        self, identity: WorkloadIdentity, capability: str
    ) -> TenantAccessGrant:
        return await self.delegate.authorize_workload(identity, capability)

    @override
    async def enabled_tenant_ids(self) -> tuple[str, ...]:
        return await self.delegate.enabled_tenant_ids()
