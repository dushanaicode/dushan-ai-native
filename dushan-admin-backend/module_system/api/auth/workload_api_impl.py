from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.auth.workload_api import WorkloadApi
from module_system.service.auth.system_workload_service import SystemWorkloadService


@service(interface=WorkloadApi)
class WorkloadApiImpl(WorkloadApi):
    workloads: SystemWorkloadService = Inject()

    def scope(self, capability, tenant_id):
        return self.workloads.scope(capability, tenant_id)
