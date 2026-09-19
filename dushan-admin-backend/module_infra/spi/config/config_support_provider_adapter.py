from framework.starter_config.public import (
    ConfigProvider,
    ConfigSettings,
)
from framework.starter_di.public import (
    Inject,
    framework,
)
from framework.starter_tenant.public import (
    TenantSettings,
)
from module_infra.service.config.config_data_service import ConfigDataService
from module_system.api.auth.workload_api import WorkloadApi


@framework
class ConfigSupportProviderAdapter:
    service: ConfigDataService = Inject()
    configuration: ConfigProvider = Inject()
    settings: ConfigSettings = Inject()
    tenant: TenantSettings = Inject()
    workloads: WorkloadApi = Inject()

    async def refresh(self):
        async with self.workloads.scope("infra.config.sync", self.tenant.default_tenant_id):
            return await self.configuration.refresh_external(self.service.get_config_map)
