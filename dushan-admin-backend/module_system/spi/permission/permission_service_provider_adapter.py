from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    LoginSession,
    PermissionProvider,
    PermissionSnapshot,
)
from module_system.service.permission.permission_service import PermissionService


@service(interface=PermissionProvider)
class PermissionServiceProviderAdapter(PermissionProvider):
    delegate: PermissionService = Inject()

    @override
    async def snapshot(self, session: LoginSession, *, binding: str) -> PermissionSnapshot:
        return await self.delegate.permission_snapshot(session, binding=binding)
