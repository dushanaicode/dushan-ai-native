from typing import override

from framework.starter_data_permission.public import (
    DataExemptionProvider,
)
from framework.starter_data_permission.spi.data_exemption_provider import DataOperation
from framework.starter_di.public import (
    service,
)
from framework.starter_security.public import (
    LoginSession,
    WorkloadIdentity,
)
from module_system.definitions.constants.workload_constants import WorkloadConstants


@service(interface=DataExemptionProvider)
class SystemDataExemptionProvider(DataExemptionProvider):
    @override
    async def workload_resources(
        self, identity: WorkloadIdentity, capability: str
    ) -> dict[str, frozenset[DataOperation]]:
        """只提供当前租户工作负载单项能力声明的受保护资源。"""
        if identity.tenant_id is None or capability not in identity.capabilities:
            return {}
        definition = WorkloadConstants.CAPABILITIES.get(capability)
        if definition is None:
            return {}
        return {
            resource: actions
            for resource, actions in definition["resources"].items()
            if resource in WorkloadConstants.PROTECTED
        }

    @override
    async def authorize(
        self,
        identity: LoginSession | WorkloadIdentity,
        resource: str,
        operation: DataOperation,
        reason: str,
    ) -> bool:
        """仅允许租户工作负载豁免其已登记能力声明的资源动作。"""
        if not isinstance(identity, WorkloadIdentity) or reason not in identity.capabilities:
            return False
        definition = WorkloadConstants.CAPABILITIES.get(reason)
        if definition is None:
            return False
        resources = definition["resources"]
        return (
            identity.tenant_id is not None
            and resource in resources
            and operation in resources[resource]
        )
