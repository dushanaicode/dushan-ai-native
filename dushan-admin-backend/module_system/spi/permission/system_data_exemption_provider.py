from framework.starter_data_permission.public import (
    DataExemptionProvider,
)
from framework.starter_di.public import (
    service,
)
from framework.starter_security.public import (
    WorkloadIdentity,
)
from module_system.definitions.constants.workload_constants import WorkloadConstants


@service(interface=DataExemptionProvider)
class SystemDataExemptionProvider(DataExemptionProvider):
    async def authorize(self, identity, resource, operation, reason):
        if not isinstance(identity, WorkloadIdentity) or reason not in identity.capabilities:
            return False
        resources = WorkloadConstants.RESOURCES.get(reason, {})
        return (
            identity.tenant_id is not None
            and resource in resources
            and operation in resources[resource]
        )
