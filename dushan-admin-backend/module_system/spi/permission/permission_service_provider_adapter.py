from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    PermissionProvider,
)
from module_system.service.permission.permission_service import PermissionService


@service(interface=PermissionProvider)
class PermissionServiceProviderAdapter(PermissionProvider):
    delegate: PermissionService = Inject()

    async def snapshot(self, session, *, binding: str):
        return await self.delegate.permission_snapshot(session, binding=binding)
