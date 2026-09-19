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
from module_infra.controller.admin.config.vo.type.type_page_req_vo import ConfigTypePageReqVO
from module_infra.dal.dataobject.config.config_type_do import InfraConfigTypeDO


@mapper()
class ConfigTypeMapper(BaseMapper[InfraConfigTypeDO]):
    def __init__(self):
        super().__init__(InfraConfigTypeDO)

    async def select_page(self, req_vo: ConfigTypePageReqVO) -> PageResult[InfraConfigTypeDO]:
        """根据分页请求查询配置类型数据，并返回分页结果"""
        stmt = select(InfraConfigTypeDO)
        if req_vo.module:
            stmt = stmt.where(InfraConfigTypeDO.module == req_vo.module)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(InfraConfigTypeDO.name.ilike(f"%{escaped}%"))
        if req_vo.code:
            escaped_code = StrUtils.escape_like(req_vo.code)
            stmt = stmt.where(InfraConfigTypeDO.code.ilike(f"%{escaped_code}%"))
        if req_vo.status is not None:
            stmt = stmt.where(InfraConfigTypeDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                InfraConfigTypeDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        return await self.paginate_query(stmt, req_vo)

    async def select_by_code(self, code: str) -> InfraConfigTypeDO | None:
        """根据配置类型编码查询记录"""
        stmt = select(InfraConfigTypeDO).where(InfraConfigTypeDO.code == code)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_name(self, name: str) -> InfraConfigTypeDO | None:
        """根据配置类型名称查询记录"""
        stmt = select(InfraConfigTypeDO).where(InfraConfigTypeDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def update_to_delete(self, config_type_id: int, deleted_time: datetime) -> None:
        """逻辑删除配置类型记录，同时更新删除时间"""
        stmt = (
            update(InfraConfigTypeDO)
            .where(InfraConfigTypeDO.id == config_type_id)
            .values(deleted=True, deleted_time=deleted_time)
        )
        await self.write(stmt)

    async def select_list(self) -> list[InfraConfigTypeDO]:
        """查询所有未逻辑删除的配置类型记录"""
        stmt = select(InfraConfigTypeDO)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_field(self, field: str, value: Any) -> list[InfraConfigTypeDO]:
        """根据指定字段查询配置类型数据列表"""
        column = InfraConfigTypeDO.__table__.c.get(field)
        if column is None:
            raise ValueError(f"字段 {field} 不存在于 InfraConfigTypeDO")
        condition: BinaryExpression = column.__eq__(value)
        stmt = select(InfraConfigTypeDO).where(condition)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_list_by_module(self, module: str) -> list[InfraConfigTypeDO]:
        """根据模块标识查询所有启用的配置类型"""
        stmt = (
            select(InfraConfigTypeDO)
            .where(InfraConfigTypeDO.module == module, InfraConfigTypeDO.status == 0)
            .order_by(InfraConfigTypeDO.id.asc())
        )
        result = await self.read(stmt)
        return list(result.scalars().all())
