from __future__ import annotations

from typing import override

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.tenant.dto.tenant_package_resp_dto import TenantPackageRespDTO
from module_system.api.tenant.tenant_package_api import TenantPackageApi
from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.service.tenant.tenant_package_service import TenantPackageService
from module_system.service.tenant.tenant_service import TenantService


@service(interface=TenantPackageApi)
class TenantPackageApiImpl(TenantPackageApi):
    """租户套餐 API 实现类"""

    tenant_package_service: TenantPackageService = Inject()
    tenant_service: TenantService = Inject()

    @override
    async def get_tenant_package(self, package_id: int) -> TenantPackageRespDTO | None:
        do = await self.tenant_package_service.get_tenant_package(package_id)
        if not do:
            return None
        return TenantPackageRespDTO.model_validate(do)

    @override
    async def get_tenant_package_by_tenant_id(self, tenant_id: int) -> TenantPackageRespDTO | None:
        tenant = await self.tenant_service.get_tenant(tenant_id)
        if not tenant:
            return None
        if tenant.package_id == TenantDO.PACKAGE_ID_SYSTEM:
            return None
        return await self.get_tenant_package(tenant.package_id)
