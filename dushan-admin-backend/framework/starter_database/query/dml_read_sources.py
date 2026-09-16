from sqlalchemy import Table, Update
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.selectable import Alias, Select
from sqlalchemy.sql.util import ClauseAdapter


class DmlReadSources:
    """DML 裸 FROM/USING 来源的读条件；子查询由统一行重写器处理。"""

    @staticmethod
    def sources(statement):
        sources = set()
        pending = list(statement._where_criteria)
        if isinstance(statement, Update):
            pending.extend((statement._values or {}).values())
            pending.extend(value for _, value in (statement._ordered_values or ()))
        while pending:
            node = pending.pop()
            if isinstance(node, Select):
                continue
            if isinstance(node, ColumnClause):
                source = node.table
                if (
                    isinstance(source, Table)
                    and source._deannotate() is not statement.table._deannotate()
                ):
                    sources.add((source, source._deannotate()))
                elif isinstance(source, Alias) and isinstance(source.element, Table):
                    sources.add((source, source.element._deannotate()))
            pending.extend(node.get_children())
        return sources

    @classmethod
    def filter(cls, statement, registry, builder):
        sources = cls.sources(statement)
        if not sources:
            return statement
        return statement.where(
            *(
                ClauseAdapter(source).traverse(builder.condition(registry.require(table), "select"))
                for source, table in sources
            )
        )
