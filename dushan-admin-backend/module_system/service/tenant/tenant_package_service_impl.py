from __future__ import annotations

from typing import override

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_cache.public import CacheHandler, cache
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_page_req_vo import (
    TenantPackagePageReqVO,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_save_req_vo import (
    TenantPackageSaveReqVO,
)
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.cache.tenant.dto.tenant_package_cache_dto import TenantPackageCacheDTO
from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.dal.dataobject.tenant.tenant_package_do import TenantPackageDO
from module_system.dal.mapper.tenant.tenant_package_mapper import TenantPackageMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.tenant.tenant_package_service import TenantPackageService
from module_system.service.tenant.tenant_service import TenantService


@service(interface=TenantPackageService)
class TenantPackageServiceImpl(TenantPackageService):
    cache_handler: CacheHandler = Inject()
    database: SessionProvider = Inject()
    tenant_package_mapper: TenantPackageMapper = Inject()
    tenant_service: TenantService = Inject()
    default_ttl: int = 3600

    @override
    @transactional
    async def create_tenant_package(self, create_req_vo: TenantPackageSaveReqVO) -> int:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.TENANT_PACKAGE),
            required=True,
            name="system-cache",
        )
        await self._validate_tenant_package_name_unique(None, create_req_vo.name)
        tenant_package = TenantPackageDO(**create_req_vo.model_dump(by_alias=False))
        await self.tenant_package_mapper.insert(tenant_package)
        return tenant_package.id

    @override
    @transactional
    async def update_tenant_package(self, update_req_vo: TenantPackageSaveReqVO) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.TENANT_PACKAGE),
            required=True,
            name="system-cache",
        )
        tenant_package = await self._validate_tenant_package_exists(update_req_vo.id)
        await self._validate_tenant_package_name_unique(update_req_vo.id, update_req_vo.name)
        update_obj = TenantPackageDO(**update_req_vo.model_dump(by_alias=False))
        await self.tenant_package_mapper.update_by_id(update_obj)
        if tenant_package.menu_ids != update_req_vo.menu_ids:
            tenants: list[TenantDO] = await self.tenant_service.get_tenant_list_by_package_id(
                tenant_package.id
            )
            for tenant in tenants:
                menu_ids_set: set[int] = set(update_req_vo.menu_ids or [])
                await self.tenant_service.update_tenant_role_menu(tenant.id, menu_ids_set)

    @override
    @transactional
    async def update_status(self, package_id: int, status: int) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.TENANT_PACKAGE),
            required=True,
            name="system-cache",
        )
        "更新租户套餐状态"
        await self._validate_tenant_package_exists(package_id)
        update_obj = TenantPackageDO(id=package_id, status=status)
        await self.tenant_package_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_tenant_package(self, id: int) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.TENANT_PACKAGE),
            required=True,
            name="system-cache",
        )
        await self._validate_tenant_package_exists(id)
        await self._validate_tenant_used(id)
        await self.tenant_package_mapper.delete_by_id(id)

    @override
    @transactional
    async def delete_tenant_package_batch(self, ids: list[int]) -> int:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.TENANT_PACKAGE),
            required=True,
            name="system-cache",
        )
        for package_id in ids:
            await self._validate_tenant_package_exists(package_id)
            await self._validate_tenant_used(package_id)
        return await self.tenant_package_mapper.delete_by_ids(ids)

    @cache(
        SystemCacheKeys.TENANT_PACKAGE,
        key="id:{{id}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: not result is not None,
    )
    @override
    async def get_tenant_package(self, id: int) -> TenantPackageCacheDTO:
        loaded = await self.tenant_package_mapper.select_by_id(id)
        return None if loaded is None else TenantPackageCacheDTO.model_validate(loaded)

    @override
    async def get_tenant_package_page(
        self, page_req_vo: TenantPackagePageReqVO
    ) -> PageResult[TenantPackageDO]:
        return await self.tenant_package_mapper.select_page(page_req_vo)

    @cache(
        SystemCacheKeys.TENANT_PACKAGE,
        key="id:{{id}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: not result is not None,
    )
    @override
    async def valid_tenant_package(self, id: int) -> TenantPackageCacheDTO:
        tenant_package = await self.tenant_package_mapper.select_by_id(id)
        if tenant_package is None:
            raise ServiceException(ErrorCodeConstants.TENANT_PACKAGE_NOT_EXISTS)
        if tenant_package.status == StatusEnum.DISABLE.code:
            raise ServiceException(ErrorCodeConstants.TENANT_PACKAGE_DISABLE, tenant_package.name)
        loaded = tenant_package
        return None if loaded is None else TenantPackageCacheDTO.model_validate(loaded)

    @override
    async def get_tenant_package_list_by_status(self, status: int) -> list[TenantPackageDO]:
        return await self.tenant_package_mapper.select_list_by_status(status)

    async def _validate_tenant_package_exists(self, id: int) -> TenantPackageDO:
        tenant_package = await self.tenant_package_mapper.select_by_id(id)
        if tenant_package is None:
            raise ServiceException(ErrorCodeConstants.TENANT_PACKAGE_NOT_EXISTS)
        return tenant_package

    async def _validate_tenant_used(self, id: int) -> None:
        count = await self.tenant_service.get_tenant_count_by_package_id(id)
        if count > 0:
            raise ServiceException(ErrorCodeConstants.TENANT_PACKAGE_USED)

    async def _validate_tenant_package_name_unique(self, id: int | None, name: str) -> None:
        if not name or name.strip() == "":
            return
        tenant_package = await self.tenant_package_mapper.select_by_name(name)
        if tenant_package is None:
            return
        if id is None or tenant_package.id != id:
            raise ServiceException(ErrorCodeConstants.TENANT_PACKAGE_NAME_DUPLICATE)
