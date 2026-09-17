from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.auth.workload_api import WorkloadApi
from module_system.service.auth.system_workload_service import SystemWorkloadService


@service(interface=WorkloadApi)
class WorkloadApiImpl(WorkloadApi):
    workloads: SystemWorkloadService = Inject()

    def scope(self, capability, tenant_id):
        return self.workloads.scope(capability, tenant_id)
