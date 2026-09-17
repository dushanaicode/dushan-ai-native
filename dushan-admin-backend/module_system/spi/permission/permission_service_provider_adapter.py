from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.spi.permission_provider import PermissionProvider
from module_system.service.permission.permission_service import PermissionService


@service(interface=PermissionProvider)
class PermissionServiceProviderAdapter(PermissionProvider):
    delegate: PermissionService = Inject()

    async def snapshot(self, session, *, binding: str):
        return await self.delegate.permission_snapshot(session, binding=binding)
