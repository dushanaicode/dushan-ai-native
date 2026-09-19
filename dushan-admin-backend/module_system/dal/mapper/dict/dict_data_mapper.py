from __future__ import annotations

from collections.abc import Collection
from typing import Any

from sqlalchemy import BinaryExpression, func, select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.controller.admin.dict.vo.data.data_page_req_vo import DictDataPageReqVO
from module_system.dal.dataobject.dict.dict_data_do import DictDataDO


@mapper()
class DictDataMapper(BaseMapper[DictDataDO]):
    def __init__(self):
        super().__init__(DictDataDO)

    async def select_by_dict_type_and_value(self, dict_type: str, value: str) -> DictDataDO | None:
        stmt = select(DictDataDO).where(
            DictDataDO.dict_type == dict_type, DictDataDO.value == value
        )
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_dict_type_and_label(self, dict_type: str, label: str) -> DictDataDO | None:
        stmt = select(DictDataDO).where(
            DictDataDO.dict_type == dict_type, DictDataDO.label == label
        )
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_dict_type_and_values(
        self, dict_type: str, values: Collection[str]
    ) -> list[DictDataDO]:
        stmt = select(DictDataDO).where(
            DictDataDO.dict_type == dict_type, DictDataDO.value.in_(values)
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def delete_by_dict_type(self, dict_type: str) -> int:
        stmt = select(func.count()).select_from(DictDataDO).where(DictDataDO.dict_type == dict_type)
        result = await self.read(stmt)
        return result.scalar_one()

    async def select_count_by_dict_type(self, dict_type: str) -> int:
        stmt = select(func.count(DictDataDO.id)).where(DictDataDO.dict_type == dict_type)
        result = await self.read(stmt)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

    async def select_page(self, req_vo: DictDataPageReqVO) -> PageResult[DictDataDO]:
        stmt = select(DictDataDO)
        if req_vo.label:
            escaped = StrUtils.escape_like(req_vo.label)
            stmt = stmt.where(DictDataDO.label.ilike(f"%{escaped}%"))
        if req_vo.dict_type:
            stmt = stmt.where(DictDataDO.dict_type == req_vo.dict_type)
        if req_vo.status is not None:
            stmt = stmt.where(DictDataDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                DictDataDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(DictDataDO.dict_type.desc(), DictDataDO.sort.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_list_by_status_and_dict_type(
        self, status: int, dict_type: str | None
    ) -> list[DictDataDO]:
        stmt = select(DictDataDO).where(DictDataDO.status == status)
        if dict_type is not None:
            stmt = stmt.where(DictDataDO.dict_type == dict_type)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_field(self, field: str, value: Any) -> list[DictDataDO]:
        column = DictDataDO.__table__.c.get(field)
        if column is None:
            raise ValueError(f"字段 {field} 不存在于 DictDataDO")
        condition: BinaryExpression = column.__eq__(value)
        stmt = select(DictDataDO).where(condition)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_dict_types(self, dict_types: list[str]) -> list[DictDataDO]:
        if not dict_types:
            return []
        stmt = select(DictDataDO).where(DictDataDO.dict_type.in_(dict_types))
        result = await self.read(stmt)
        return list(result.scalars().all())
