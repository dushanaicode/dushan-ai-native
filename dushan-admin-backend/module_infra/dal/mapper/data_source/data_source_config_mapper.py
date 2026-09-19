from __future__ import annotations

from sqlalchemy import select

from framework.common.enums import StatusEnum
from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_infra.controller.admin.data_source.vo.data_source_config_page_req_vo import (
    DataSourceConfigPageReqVO,
)
from module_infra.dal.dataobject.data_source.data_source_config_do import DataSourceConfigDO


@mapper()
class DataSourceConfigMapper(BaseMapper[DataSourceConfigDO]):
    def __init__(self):
        super().__init__(DataSourceConfigDO)

    async def select_page(
        self, req_vo: DataSourceConfigPageReqVO
    ) -> PageResult[DataSourceConfigDO]:
        """分页查询数据源配置"""
        stmt = select(DataSourceConfigDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(DataSourceConfigDO.name.ilike(f"%{escaped}%"))
        if req_vo.status is not None:
            stmt = stmt.where(DataSourceConfigDO.status == req_vo.status)
        if req_vo.db_type:
            stmt = stmt.where(DataSourceConfigDO.db_type == req_vo.db_type)
        if req_vo.source_type is not None:
            stmt = stmt.where(DataSourceConfigDO.source_type == req_vo.source_type)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                DataSourceConfigDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(DataSourceConfigDO.create_time.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_list_by_status(self, status: int) -> list[DataSourceConfigDO]:
        """根据状态查询数据源配置列表"""
        stmt = select(DataSourceConfigDO).where(DataSourceConfigDO.status == status)
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_by_name(self, name: str) -> DataSourceConfigDO | None:
        """根据名称查询数据源配置"""
        stmt = select(DataSourceConfigDO).where(DataSourceConfigDO.name == name)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_default_datasource(self, source_type: int) -> DataSourceConfigDO | None:
        """查询默认数据源"""
        stmt = select(DataSourceConfigDO).where(
            DataSourceConfigDO.is_default.is_(True),
            DataSourceConfigDO.source_type == source_type,
            DataSourceConfigDO.status == StatusEnum.ENABLE.code,
        )
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list(self) -> list[DataSourceConfigDO]:
        """查询所有数据源配置列表"""
        stmt = select(DataSourceConfigDO)
        result = await self.read(stmt)
        return list(result.scalars().all())
