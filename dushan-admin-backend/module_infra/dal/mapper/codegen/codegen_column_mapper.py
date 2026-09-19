from __future__ import annotations

from sqlalchemy import select

from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO


@mapper()
class CodegenColumnMapper(BaseMapper[CodegenColumnDO]):
    def __init__(self):
        super().__init__(CodegenColumnDO)

    async def select_list_by_table_id(self, table_id: int) -> list[CodegenColumnDO]:
        """根据表编号查询列列表"""
        stmt = (
            select(CodegenColumnDO)
            .where(CodegenColumnDO.table_id == table_id)
            .order_by(CodegenColumnDO.order_no.asc())
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def delete_by_table_id(self, table_id: int) -> None:
        """根据表编号删除列"""
        columns = await self.select_list_by_table_id(table_id)
        for column in columns:
            await self.delete_by_id(column.id)
