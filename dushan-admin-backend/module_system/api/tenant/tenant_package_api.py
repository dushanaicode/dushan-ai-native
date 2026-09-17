from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.tenant.dto.tenant_package_resp_dto import TenantPackageRespDTO


@runtime_checkable
class TenantPackageApi(Protocol):
    """租户套餐 API 接口（跨模块调用）

    供其他模块获取套餐信息及配额模板。
    """

    async def get_tenant_package(self, package_id: int) -> TenantPackageRespDTO | None:
        """根据套餐编号获取套餐信息（含 quota_config）"""
        ...

    async def get_tenant_package_by_tenant_id(self, tenant_id: int) -> TenantPackageRespDTO | None:
        """根据租户编号获取其所属套餐信息（含 quota_config）"""
        ...
