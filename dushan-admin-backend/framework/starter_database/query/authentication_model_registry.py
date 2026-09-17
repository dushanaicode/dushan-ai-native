from types import MappingProxyType, SimpleNamespace

from sqlalchemy import Column, Delete, Insert, Table, Update, inspect
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import ColumnClause, TextClause
from sqlalchemy.sql.selectable import Select, TableClause


class AuthenticationModelRegistry:
    """认证仓储构造时冻结的表白名单；同名伪造表、文本 SQL 和嵌套写入均拒绝。"""

    def __init__(self, models):
        entries = {}
        for model in models:
            mapper = inspect(model)
            table = mapper.local_table
            if len(mapper.tables) != 1 or table.key in entries:
                raise ValueError("认证读取只允许唯一的单表模型")
            entries[table.key] = SimpleNamespace(
                table=table,
                model=model,
                public=False,
                tenant_column="tenant_id" if "tenant_id" in table.c else None,
            )
        self.entries = MappingProxyType(entries)

    def require(self, table):
        config = self.entries.get(table.key)
        if config is None or table._deannotate() is not config.table:
            raise ValueError("认证读取不能访问未登记的表")
        return config

    def require_mapper(self, mapper):
        config = self.require(mapper.local_table)
        if config.model is not mapper.class_:
            raise ValueError("认证模型与表不匹配")
        return config

    def validate_statement(self, statement):
        if not isinstance(statement, Select):
            raise ValueError("认证入口只允许 SELECT")
        tables, pending, seen = set(), [statement], set()
        while pending:
            node = pending.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            if isinstance(node, (Insert, Update, Delete, TextClause)):
                raise ValueError("认证入口不允许文本 SQL 或写入")
            if isinstance(node, TableClause) and not isinstance(node, Table):
                raise ValueError("认证入口不允许未映射表")
            if (
                isinstance(node, ColumnClause)
                and node.is_literal
                and str(node.name) not in {"1", "*"}
            ):
                raise ValueError("认证入口不允许字面 SQL 列")
            entity = node._annotations.get("parententity")
            if entity is not None:
                self.require_mapper(entity.mapper if entity.is_aliased_class else entity)
            if isinstance(node, Table):
                tables.add(self.require(node).table)
            if isinstance(node, Column) and isinstance(node.table, Table):
                tables.add(self.require(node.table).table)
            if isinstance(node, Select):
                if (
                    node._for_update_arg is not None
                    or node._prefixes
                    or node._suffixes
                    or node._hints
                    or node._statement_hints
                ):
                    raise ValueError("认证读取不允许加锁或 SQL 提示")
                pending.extend(node.selected_columns)
                for source in node.get_final_froms():
                    pending.extend(visitors.iterate(source))
            pending.extend(node.get_children())
        return tables
