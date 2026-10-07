from dmSQLAlchemy.base import DMDDLCompiler
from sqlalchemy import Table, UniqueConstraint, event
from sqlalchemy.schema import AddConstraint


class DmDdlCompiler(DMDDLCompiler):
    """达梦虚拟列的唯一性通过唯一索引实现，不能使用表级 UNIQUE 约束。"""

    @staticmethod
    def computed_unique_constraints(table):
        """按名称返回包含虚拟列的唯一约束，不改变共享模型元数据。"""
        return sorted(
            (
                constraint
                for constraint in table.constraints
                if isinstance(constraint, UniqueConstraint)
                and any(column.computed is not None for column in constraint)
            ),
            key=DmDdlCompiler.index_name,
        )

    @staticmethod
    def index_name(constraint):
        """未命名的约束从表名和列名生成确定的索引名称。"""
        return constraint.name or (
            f"uq_{constraint.table.name}_" + "_".join(column.name for column in constraint)
        )

    def visit_unique_constraint(self, constraint, **kwargs):
        if any(column.computed is not None for column in constraint):
            return None
        return super().visit_unique_constraint(constraint, **kwargs)

    def visit_add_constraint(self, create, **kwargs):
        constraint = create.element
        if isinstance(constraint, UniqueConstraint) and any(
            column.computed is not None for column in constraint
        ):
            name = self.preparer.quote(self.index_name(constraint))
            table = self.preparer.format_table(constraint.table)
            columns = [self.preparer.quote(column.name) for column in constraint]
            present = " AND ".join(
                f"{self.preparer.quote(column.name)} IS NOT NULL"
                for column in constraint
                if column.nullable or column.computed is not None
            )
            # DM 把复合键中的 NULL 当作相等；含 NULL 的记录用主键区分。
            # 只追加判别表达式，避免长复合键为每列重复 CASE 超出 DM 表达式限制。
            columns.extend(
                f"CASE WHEN {present} THEN NULL ELSE {self.preparer.quote(column.name)} END"
                for column in constraint.table.primary_key
            )
            return f"CREATE UNIQUE INDEX {name} ON {table} ({', '.join(columns)})"
        return super().visit_add_constraint(create, **kwargs)

    @staticmethod
    def create_computed_unique_indexes(table, connection, **kwargs):
        """Table.create/create_all 在达梦建表后创建虚拟列唯一索引。"""
        if connection.dialect.name == "dm":
            for constraint in DmDdlCompiler.computed_unique_constraints(table):
                connection.execute(AddConstraint(constraint, isolate_from_table=False))


event.listen(Table, "after_create", DmDdlCompiler.create_computed_unique_indexes)
