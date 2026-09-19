from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    WorkloadProvider,
)
from module_system.service.auth.system_workload_service import SystemWorkloadService


@service(interface=WorkloadProvider)
class SystemWorkloadProvider(WorkloadProvider):
    delegate: SystemWorkloadService = Inject()

    async def authenticate(
        self,
        source: str,
        *,
        application_id: str,
        domain: str,
        capability: str,
        tenant_id: str | None,
    ):
        return await self.delegate.authenticate(
            source,
            application_id=application_id,
            domain=domain,
            capability=capability,
            tenant_id=tenant_id,
        )
