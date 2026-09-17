from __future__ import annotations

import json

from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_system.controller.admin.tenant.vo.packages.packages_package_page_req_vo import (
    TenantPackagePageReqVO,
)
from module_system.dal.dataobject.tenant.tenant_package_do import TenantPackageDO


@mapper()
class TenantPackageMapper(BaseMapper[TenantPackageDO]):
    def __init__(self):
        super().__init__(TenantPackageDO)

    def _convert_row(self, obj: TenantPackageDO) -> TenantPackageDO:
        if isinstance(obj.menu_ids, str):
            obj.menu_ids = set(json.loads(obj.menu_ids))
        return obj

    async def select_page(self, req_vo: TenantPackagePageReqVO) -> PageResult[TenantPackageDO]:
        stmt = select(TenantPackageDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(TenantPackageDO.name.ilike(f"%{escaped}%"))
        if req_vo.status is not None:
            stmt = stmt.where(TenantPackageDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                TenantPackageDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(TenantPackageDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_list_by_status(self, status: int) -> list[TenantPackageDO]:
        stmt = select(TenantPackageDO).where(TenantPackageDO.status == status)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_by_name(self, name: str) -> TenantPackageDO | None:
        stmt = select(TenantPackageDO).where(TenantPackageDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
