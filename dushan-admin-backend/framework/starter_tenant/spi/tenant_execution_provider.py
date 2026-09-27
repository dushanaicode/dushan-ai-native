from collections.abc import AsyncIterator
from typing import Protocol

from framework.starter_tenant.context.tenant_context import TenantContext


class TenantExecutionProvider(Protocol):
    """后台任务和消息的租户执行视图，目标批次由租户组件验证。"""

    @property
    def ready(self) -> bool: ...

    @property
    def context(self) -> TenantContext: ...

    def target_batches(self) -> AsyncIterator[tuple[str, ...]]: ...
