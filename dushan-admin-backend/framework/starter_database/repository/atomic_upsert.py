from sqlalchemy import and_, case, false
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.dml import Insert


class AtomicUpsert(Insert):
    """受管单行原子写入；冲突仅更新业务列，不复活软删除记录。"""

    inherit_cache = False

    def __init__(self, table, conflict_columns, update_columns):
        super().__init__(table)
        self.conflict_columns = tuple(conflict_columns)
        self.update_columns = tuple(update_columns)
        self.audit_update_columns = ("update_time",)

    def compile_native(self, compiler, **kwargs):
        """按目标方言编译原子写入，保留审计与软删除约束。"""
        dialect = compiler.dialect.name
        table = self.table
        values = self._values
        columns = (*self.update_columns, *self.audit_update_columns)
        if dialect in {"postgresql", "opengauss", "kingbase", "sqlite"}:
            factory = sqlite_insert if dialect == "sqlite" else postgresql_insert
            native = factory(table).values(values)
            native = native.on_conflict_do_update(
                index_elements=[table.c[name] for name in self.conflict_columns],
                set_={name: native.excluded[name] for name in columns},
                where=table.c.deleted == false(),
            )
            return compiler.process(native, **kwargs)
        if dialect in {"mysql", "mariadb", "oceanbase"}:
            native = mysql_insert(table).values(values)
            eligible = and_(
                table.c.deleted == false(),
                *(table.c[name] == native.inserted[name] for name in self.conflict_columns),
            )
            native = native.on_duplicate_key_update(
                [
                    (name, case((eligible, native.inserted[name]), else_=table.c[name]))
                    for name in columns
                ]
            )
            return compiler.process(native, **kwargs)
        if dialect == "dm":
            # DM 的 MERGE 使用 DUAL 单行源；所有标识符与值都交由方言编译器处理。
            quote = compiler.preparer.quote
            target = compiler.preparer.format_table(table)
            names = [column.key if hasattr(column, "key") else column for column in values]
            source = ", ".join(
                f"{compiler.process(value._with_binary_element_type(table.c[name].type), **kwargs)} AS {quote(name)}"
                for name, value in zip(names, values.values(), strict=True)
            )
            match = " AND ".join(
                f"t.{quote(name)} = s.{quote(name)}" for name in self.conflict_columns
            )
            assignments = ", ".join(f"t.{quote(name)} = s.{quote(name)}" for name in columns)
            insert_columns = ", ".join(quote(name) for name in names)
            insert_values = ", ".join(f"s.{quote(name)}" for name in names)
            return (
                f"MERGE INTO {target} t USING (SELECT {source} FROM DUAL) s ON ({match}) "
                f"WHEN MATCHED THEN UPDATE SET {assignments} WHERE t.{quote('deleted')} = 0 "
                f"WHEN NOT MATCHED THEN INSERT ({insert_columns}) VALUES ({insert_values})"
            )
        raise NotImplementedError(f"方言 {dialect} 尚未实现原子 upsert")


@compiles(AtomicUpsert)
def compile_atomic_upsert(statement, compiler, **kwargs):
    return statement.compile_native(compiler, **kwargs)
