from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.controller.admin.tenant.vo.packages.packages_package_page_req_vo import (
    TenantPackagePageReqVO,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_save_req_vo import (
    TenantPackageSaveReqVO,
)
from module_system.dal.cache.tenant.dto.tenant_package_cache_dto import TenantPackageCacheDTO
from module_system.dal.dataobject.tenant.tenant_package_do import TenantPackageDO


@runtime_checkable
class TenantPackageService(Protocol):
    async def create_tenant_package(self, create_req_vo: TenantPackageSaveReqVO) -> int: ...

    async def update_tenant_package(self, update_req_vo: TenantPackageSaveReqVO) -> None: ...

    async def update_status(self, package_id: int, status: int) -> None: ...

    async def delete_tenant_package(self, id: int) -> None: ...

    async def delete_tenant_package_batch(self, ids: list[int]) -> int: ...

    async def get_tenant_package(self, id: int) -> TenantPackageCacheDTO: ...

    async def get_tenant_package_page(
        self, page_req_vo: TenantPackagePageReqVO
    ) -> PageResult[TenantPackageDO]: ...

    async def valid_tenant_package(self, id: int) -> TenantPackageCacheDTO: ...

    async def get_tenant_package_list_by_status(self, status: int) -> list[TenantPackageDO]: ...
