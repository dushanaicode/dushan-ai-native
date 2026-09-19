from __future__ import annotations

from sqlalchemy import select

from framework.common.page import PageResult
from framework.common.utils import StrUtils
from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_infra.controller.admin.codegen.vo.codegen_table_page_req_vo import CodegenTablePageReqVO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO


@mapper()
class CodegenTableMapper(BaseMapper[CodegenTableDO]):
    def __init__(self):
        super().__init__(CodegenTableDO)

    async def select_page(self, req_vo: CodegenTablePageReqVO) -> PageResult[CodegenTableDO]:
        """分页查询代码生成表定义"""
        stmt = select(CodegenTableDO)
        if req_vo.table_name:
            escaped_tn = StrUtils.escape_like(req_vo.table_name)
            stmt = stmt.where(CodegenTableDO.table_name.ilike(f"%{escaped_tn}%"))
        if req_vo.table_comment:
            escaped_tc = StrUtils.escape_like(req_vo.table_comment)
            stmt = stmt.where(CodegenTableDO.table_comment.ilike(f"%{escaped_tc}%"))
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                CodegenTableDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(CodegenTableDO.update_time.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_list_by_data_source_config_id(
        self, data_source_config_id: int
    ) -> list[CodegenTableDO]:
        """根据数据源配置ID查询列表"""
        stmt = select(CodegenTableDO).where(
            CodegenTableDO.data_source_config_id == data_source_config_id
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def select_by_table_name_and_data_source(
        self, table_name: str, data_source_config_id: int
    ) -> CodegenTableDO | None:
        """根据表名和数据源查询"""
        stmt = select(CodegenTableDO).where(
            CodegenTableDO.table_name == table_name,
            CodegenTableDO.data_source_config_id == data_source_config_id,
        )
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_list_by_master_table_id(self, master_table_id: int) -> list[CodegenTableDO]:
        """根据主表ID查询所有子表"""
        stmt = select(CodegenTableDO).where(CodegenTableDO.master_table_id == master_table_id)
        result = await self.read(stmt)
        return list(result.scalars().all())
