from __future__ import annotations

from sqlalchemy import func, select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_infra.controller.admin.config.vo.data.data_page_req_vo import ConfigDataPageReqVO
from module_infra.dal.dataobject.config.config_data_do import InfraConfigDataDO
from module_infra.dal.dataobject.config.config_type_do import InfraConfigTypeDO


@mapper()
class ConfigDataMapper(BaseMapper[InfraConfigDataDO]):
    def __init__(self):
        super().__init__(InfraConfigDataDO)

    async def select_by_key(self, key: str) -> InfraConfigDataDO | None:
        """根据配置键查询记录，只查询未逻辑删除的数据"""
        stmt = select(InfraConfigDataDO).where(InfraConfigDataDO.key == key)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_page(
        self, req_vo: ConfigDataPageReqVO, module_type_ids: list[int] | None = None
    ) -> PageResult[InfraConfigDataDO]:
        """分页查询配置记录"""
        stmt = select(InfraConfigDataDO)
        if module_type_ids is not None:
            stmt = stmt.where(InfraConfigDataDO.type_id.in_(module_type_ids))
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(InfraConfigDataDO.name.ilike(f"%{escaped}%"))
        if req_vo.type_id is not None:
            stmt = stmt.where(InfraConfigDataDO.type_id == req_vo.type_id)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                InfraConfigDataDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(InfraConfigDataDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_list(self) -> list[InfraConfigDataDO]:
        """查询所有配置记录（未逻辑删除）"""
        stmt = select(InfraConfigDataDO)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_ids_by_type_id(self, type_id: int) -> list[int]:
        """根据配置类型ID查询配置数据ID列表"""
        stmt = select(InfraConfigDataDO.id).where(InfraConfigDataDO.type_id == type_id)
        result = await self.read(stmt)
        return [row[0] for row in result.all()]

    async def select_count_by_type_id(self, type_id: int) -> int:
        """根据配置类型ID统计配置数量"""
        stmt = (
            select(func.count())
            .select_from(InfraConfigDataDO)
            .where(InfraConfigDataDO.type_id == type_id)
        )
        result = await self.read(stmt)
        return result.scalar_one()

    async def select_list_with_type(self) -> list[tuple[InfraConfigDataDO, InfraConfigTypeDO]]:
        """查询所有配置记录，同时关联查询配置类型信息"""
        stmt = select(InfraConfigDataDO, InfraConfigTypeDO).join(
            InfraConfigTypeDO, InfraConfigDataDO.type_id == InfraConfigTypeDO.id
        )
        result = await self.read(stmt)
        return list(result.all())

    async def select_by_key_in_types(
        self, type_ids: list[int], key: str
    ) -> InfraConfigDataDO | None:
        """根据 type_ids 和 key 查询配置"""
        stmt = select(InfraConfigDataDO).where(
            InfraConfigDataDO.type_id.in_(type_ids), InfraConfigDataDO.key == key
        )
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list_by_type_ids(self, type_ids: list[int]) -> list[InfraConfigDataDO]:
        """根据多个 type_id 查询配置列表"""
        stmt = (
            select(InfraConfigDataDO)
            .where(InfraConfigDataDO.type_id.in_(type_ids))
            .order_by(InfraConfigDataDO.type_id.asc(), InfraConfigDataDO.sort.asc())
        )
        result = await self.read(stmt)
        return list(result.scalars().all())
