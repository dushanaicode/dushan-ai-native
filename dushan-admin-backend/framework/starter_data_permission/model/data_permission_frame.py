from dataclasses import dataclass

from framework.starter_data_permission.model.data_grant import DataGrant
from framework.starter_di.context.execution_binding import ExecutionBinding
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity


@dataclass(eq=False, slots=True, repr=False)
class DataPermissionFrame:
    binding: ExecutionBinding
    identity: LoginSession | WorkloadIdentity
    grant: DataGrant
    expires_at: float
    active: bool = True
