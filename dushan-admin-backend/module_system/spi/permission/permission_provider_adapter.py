from typing import override

from framework.starter_data_permission.public import (
    DataPermissionProvider,
    DataScopeRule,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import LoginSession
from module_system.service.permission.permission_service import PermissionService


@service(interface=DataPermissionProvider)
class PermissionProviderAdapter(DataPermissionProvider):
    delegate: PermissionService = Inject()

    @override
    async def rules(self, session: LoginSession) -> tuple[DataScopeRule, ...]:
        return await self.delegate.data_rules(session)

    @override
    async def descendants(self, session: LoginSession, department_id: str) -> frozenset[str]:
        return await self.delegate.department_descendants(session, department_id)

    @override
    async def memberships(
        self, session: LoginSession, department_ids: frozenset[str]
    ) -> frozenset[str]:
        return await self.delegate.department_memberships(session, department_ids)

    @override
    async def revision(self, session: LoginSession) -> str:
        return await self.delegate.authorization_revision(session)
