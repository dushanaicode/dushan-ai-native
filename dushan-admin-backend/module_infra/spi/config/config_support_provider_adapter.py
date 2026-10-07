from typing import override

from framework.starter_config.public import (
    ConfigProvider,
    ConfigSettings,
    ConfigUpdateResult,
)
from framework.starter_config.spi.config_source_provider import ConfigSourceProvider
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_tenant.public import (
    TenantSettings,
)
from module_infra.service.config.config_data_service import ConfigDataService
from module_system.api.auth.workload_api import WorkloadApi


@service(interface=ConfigSourceProvider)
class ConfigSupportProviderAdapter(ConfigSourceProvider):
    service: ConfigDataService = Inject()
    configuration: ConfigProvider = Inject()
    settings: ConfigSettings = Inject()
    tenant: TenantSettings = Inject()
    workloads: WorkloadApi = Inject()

    @override
    async def refresh(self) -> ConfigUpdateResult:
        async with self.workloads.scope("infra.config.sync", self.tenant.default_tenant_id):
            return await self.configuration.refresh_external(self.service.get_config_map)
