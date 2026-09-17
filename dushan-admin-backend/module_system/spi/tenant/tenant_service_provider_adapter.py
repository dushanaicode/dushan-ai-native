from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_tenant.spi.tenant_directory_provider import TenantDirectoryProvider
from module_system.service.tenant.tenant_service import TenantService


@service(interface=TenantDirectoryProvider)
class TenantServiceProviderAdapter(TenantDirectoryProvider):
    delegate: TenantService = Inject()

    async def get_tenant(self, tenant_id: str):
        return await self.delegate.tenant_info(tenant_id)

    async def authorize_session(self, identity, policy):
        return await self.delegate.authorize_session(identity, policy)

    async def authorize_workload(self, identity, capability: str):
        return await self.delegate.authorize_workload(identity, capability)

    async def enabled_tenant_ids(self):
        return await self.delegate.enabled_tenant_ids()
