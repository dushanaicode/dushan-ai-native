from typing import Protocol, runtime_checkable

from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.model.workload_message import WorkloadMessage


@runtime_checkable
class SystemMessageService(Protocol):
    async def issue(self, session: LoginSession, payload: bytes, *, audience: str) -> bytes: ...
    async def verify(
        self, proof: bytes, payload: bytes, *, application_id: str, domain: str, audience: str
    ) -> LoginSession: ...
    async def issue_workload(
        self, identity: WorkloadIdentity, payload: bytes, *, audience: str, capability: str
    ) -> bytes: ...
    async def verify_workload(
        self, proof: bytes, payload: bytes, *, application_id: str, domain: str, audience: str
    ) -> WorkloadMessage: ...
