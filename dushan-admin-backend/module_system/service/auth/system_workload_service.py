from contextlib import AbstractAsyncContextManager
from typing import Protocol, runtime_checkable

from framework.starter_security.model.workload_identity import WorkloadIdentity


@runtime_checkable
class SystemWorkloadService(Protocol):
    async def authenticate(
        self, source: str, *, application_id: str, domain: str, capability: str, tenant_id: str
    ) -> WorkloadIdentity: ...
    def scope(self, capability: str, tenant_id: str) -> AbstractAsyncContextManager[None]: ...
