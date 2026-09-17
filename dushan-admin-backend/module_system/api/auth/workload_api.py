from contextlib import AbstractAsyncContextManager
from typing import Protocol


class WorkloadApi(Protocol):
    def scope(self, capability: str, tenant_id: str) -> AbstractAsyncContextManager: ...
