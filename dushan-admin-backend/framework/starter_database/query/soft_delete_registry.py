from sqlalchemy import Column, Table
from sqlalchemy.sql import visitors
from sqlalchemy.sql.selectable import Select

from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.query.row_access_target import RowAccessTarget


class SoftDeleteRegistry:
    """仅识别实际映射到 BaseDO 的表对象，不凭表名或 deleted 列推断。"""

    def __init__(self, statement):
        tables = self._tables(statement)
        self.entries = {
            mapper.local_table.key: RowAccessTarget(
                mapper.local_table, mapper.class_, False, None, ()
            )
            for mapper in BaseDO.registry.mappers
            if issubclass(mapper.class_, BaseDO) and mapper.local_table in tables
        }

    @staticmethod
    def _tables(statement):
        tables, seen, pending = set(), set(), [statement]
        while pending:
            node = pending.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            pending.extend(node.get_children())
            if isinstance(node, Table):
                tables.add(node._deannotate())
            if isinstance(node, Column) and isinstance(node.table, Table):
                tables.add(node.table._deannotate())
            if isinstance(node, Select):
                pending.extend(node.selected_columns)
                for source in node.get_final_froms():
                    pending.extend(visitors.iterate(source))
        return tables

    def require(self, table):
        return self.entries[table.key]

    def validate_statement(self, statement):
        managed = {config.table for config in self.entries.values()}
        return self._tables(statement) & managed
