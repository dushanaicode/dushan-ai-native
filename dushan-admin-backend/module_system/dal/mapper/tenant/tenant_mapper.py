from __future__ import annotations

from sqlalchemy import MergedResult, func, insert, select, update

from framework.common.page import PageResult
from framework.starter_database.model.json_array_contains import JsonArrayContains
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.tenant.vo.tenant.tenant_page_req_vo import TenantPageReqVO
from module_system.dal.dataobject.tenant.tenant_do import TenantDO


@mapper()
class TenantMapper(BaseMapper[TenantDO]):
    def __init__(self):
        super().__init__(TenantDO)

    async def select_page(self, req_vo: TenantPageReqVO) -> PageResult[TenantDO]:
        stmt = select(TenantDO)
        if req_vo.name:
            stmt = stmt.where(TenantDO.name.icontains(req_vo.name, autoescape=True, escape="\\"))
        if req_vo.contact_name:
            stmt = stmt.where(
                TenantDO.contact_name.icontains(req_vo.contact_name, autoescape=True, escape="\\")
            )
        if req_vo.contact_mobile:
            stmt = stmt.where(
                TenantDO.contact_mobile.icontains(
                    req_vo.contact_mobile, autoescape=True, escape="\\"
                )
            )
        if req_vo.status is not None:
            stmt = stmt.where(TenantDO.status == req_vo.status)
        if req_vo.create_time is not None:
            start_time, end_time = req_vo.create_time
            stmt = stmt.where(TenantDO.create_time.between(start_time, end_time))
        stmt = stmt.order_by(TenantDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_name(self, name: str) -> TenantDO | None:
        stmt = select(TenantDO).where(TenantDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_website(self, website: str) -> TenantDO | None:
        """在数据库内精确匹配域名数组，重复绑定保持唯一结果异常。"""
        stmt = select(TenantDO).where(JsonArrayContains(TenantDO.websites, website))
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_count_by_package_id(self, package_id: int) -> int:
        stmt = select(func.count()).where(TenantDO.package_id == package_id)
        result = await self.read(stmt)
        return result.scalar_one()

    async def select_list_by_package_id(self, package_id: int) -> list[TenantDO]:
        stmt = select(TenantDO).where(TenantDO.package_id == package_id)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_all(self) -> list[TenantDO]:
        stmt = select(TenantDO)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def insert_tenant(self, tenant_data: dict) -> int:
        stmt = insert(TenantDO).values(**tenant_data).returning(TenantDO.id)
        result: MergedResult = await self.write(stmt)
        new_id = result.scalar_one()
        return new_id

    async def update_tenant(self, tenant_id: str, update_data: dict) -> None:
        stmt = update(TenantDO).where(TenantDO.id == tenant_id).values(**update_data)
        await self.write(stmt)

    async def select_tenant_by_id(self, tenant_id: str) -> TenantDO | None:
        stmt = select(TenantDO).where(TenantDO.id == tenant_id)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def delete_tenant(self, tenant_id: str) -> None:
        stmt = update(TenantDO).where(TenantDO.id == tenant_id).values(deleted=True)
        await self.write(stmt)

    async def select_list_by_status(self, status: int) -> list[TenantDO]:
        stmt = select(TenantDO).where(TenantDO.status == status)
        result = await self.read(stmt)
        return list(result.scalars().all())
