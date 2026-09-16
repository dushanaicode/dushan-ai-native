from dataclasses import dataclass

from framework.starter_di.context.execution_binding import ExecutionBinding
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_tenant.model.tenant_resource_grant import TenantResourceGrant


@dataclass(eq=False, slots=True, repr=False)
class TenantFrame:
    execution: ExecutionBinding
    tenant_id: str
    identity: LoginSession | WorkloadIdentity
    resources: tuple[TenantResourceGrant, ...] | None
    expires_at: float
    available: bool = True
    active: bool = True
