from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.spi.workload_provider import WorkloadProvider
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
