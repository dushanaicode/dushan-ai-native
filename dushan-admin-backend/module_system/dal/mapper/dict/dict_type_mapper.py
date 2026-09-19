from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.sql.elements import BinaryExpression

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.dict.vo.type.type_page_req_vo import DictTypePageReqVO
from module_system.dal.dataobject.dict.dict_type_do import DictTypeDO


@mapper()
class DictTypeMapper(BaseMapper[DictTypeDO]):
    def __init__(self):
        super().__init__(DictTypeDO)

    async def select_page(self, req_vo: DictTypePageReqVO) -> PageResult[DictTypeDO]:
        stmt = select(DictTypeDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(DictTypeDO.name.ilike(f"%{escaped}%"))
        if req_vo.type:
            escaped_type = StrUtils.escape_like(req_vo.type)
            stmt = stmt.where(DictTypeDO.type.ilike(f"%{escaped_type}%"))
        if req_vo.status is not None:
            stmt = stmt.where(DictTypeDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                DictTypeDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(DictTypeDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_type(self, dict_type_str: str) -> DictTypeDO | None:
        stmt = select(DictTypeDO).where(DictTypeDO.type == dict_type_str)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_name(self, name: str) -> DictTypeDO | None:
        stmt = select(DictTypeDO).where(DictTypeDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def update_to_delete(self, dict_type_id: int, deleted_time: datetime) -> None:
        stmt = (
            update(DictTypeDO)
            .where(DictTypeDO.id == dict_type_id)
            .values(deleted=True, deleted_time=deleted_time)
        )
        await self.write(stmt)

    async def select_list(self) -> list[DictTypeDO]:
        stmt = select(DictTypeDO)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_field(self, field: str, value: Any) -> list[DictTypeDO]:
        column = DictTypeDO.__table__.c.get(field)
        if column is None:
            raise ValueError(f"字段 {field} 不存在于 DictTypeDO")
        condition: BinaryExpression = column.__eq__(value)
        stmt = select(DictTypeDO).where(condition)
        result = await self.read(stmt)
        return list(result.scalars().all())
