from framework.starter_data_permission.spi.data_permission_provider import DataPermissionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.service.permission.permission_service import PermissionService


@service(interface=DataPermissionProvider)
class PermissionProviderAdapter(DataPermissionProvider):
    delegate: PermissionService = Inject()

    async def rules(self, session):
        return await self.delegate.data_rules(session)

    async def descendants(self, session, department_id: str):
        return await self.delegate.department_descendants(session, department_id)

    async def memberships(self, session, department_ids: frozenset[str]):
        return await self.delegate.department_memberships(session, department_ids)

    async def revision(self, session):
        return await self.delegate.authorization_revision(session)
