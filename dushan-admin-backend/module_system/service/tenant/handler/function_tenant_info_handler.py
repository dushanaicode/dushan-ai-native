from __future__ import annotations

from typing import Awaitable, Callable

from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.service.tenant.handler.tenant_info_handler import TenantInfoHandler


class FunctionTenantInfoHandler(TenantInfoHandler):
    def __init__(self, func: Callable[[TenantDO], Awaitable[None]]):
        self._func = func

    async def handle(self, tenant: TenantDO) -> None:
        await self._func(tenant)
