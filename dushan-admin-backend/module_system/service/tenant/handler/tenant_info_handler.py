from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.dal.dataobject.tenant.tenant_do import TenantDO


@runtime_checkable
class TenantInfoHandler(Protocol):
    """租户信息处理器接口"""

    async def handle(self, tenant: TenantDO) -> None: ...
