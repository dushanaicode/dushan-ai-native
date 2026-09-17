from __future__ import annotations

from sqlalchemy import JSON, MergedResult, cast, func, insert, select, update

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.tenant.vo.tenant.tenant_page_req_vo import TenantPageReqVO
from module_system.dal.dataobject.tenant.tenant_do import TenantDO


@mapper()
class TenantMapper(BaseMapper[TenantDO]):
    def __init__(self):
        super().__init__(TenantDO)

    async def select_page(self, req_vo: TenantPageReqVO) -> PageResult[TenantDO]:
        stmt = select(TenantDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(TenantDO.name.ilike(f"%{escaped}%"))
        if req_vo.contact_name:
            escaped_cn = StrUtils.escape_like(req_vo.contact_name)
            stmt = stmt.where(TenantDO.contact_name.ilike(f"%{escaped_cn}%"))
        if req_vo.contact_mobile:
            escaped_cm = StrUtils.escape_like(req_vo.contact_mobile)
            stmt = stmt.where(TenantDO.contact_mobile.ilike(f"%{escaped_cm}%"))
        if req_vo.status is not None:
            stmt = stmt.where(TenantDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                TenantDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(TenantDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_name(self, name: str) -> TenantDO | None:
        stmt = select(TenantDO).where(TenantDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_website(self, website: str) -> TenantDO | None:
        stmt = select(TenantDO).where(func.json_contains(TenantDO.websites, cast(website, JSON)))
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
