from contextlib import AbstractAsyncContextManager
from typing import Protocol, runtime_checkable


@runtime_checkable
class WorkloadApi(Protocol):
    def scope(self, capability: str, tenant_id: str) -> AbstractAsyncContextManager: ...
