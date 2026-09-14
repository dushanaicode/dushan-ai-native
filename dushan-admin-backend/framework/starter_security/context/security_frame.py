from dataclasses import dataclass

from framework.starter_di.context.execution_binding import ExecutionBinding
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.request_audit import RequestAudit
from framework.starter_security.model.workload_identity import WorkloadIdentity


@dataclass(slots=True, repr=False)
class SecurityFrame:
    binding: ExecutionBinding
    session: LoginSession | None = None
    workload: WorkloadIdentity | None = None
    request_audit: RequestAudit | None = None
    active: bool = True
