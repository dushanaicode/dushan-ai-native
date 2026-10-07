from sqlalchemy import MetaData
from sqlalchemy.schema import (
    AddConstraint,
    CreateIndex,
    CreateTable,
    SetColumnComment,
    SetTableComment,
)

from framework.starter_database.ddl.ddl_dialects import DdlDialects


class DdlExporter:
    """把 SQLAlchemy 模型编译成指定数据库方言的建表语句。

    只做编译，不连接数据库。表按外键依赖排序输出，索引紧随所属表，
    保证整份脚本可从上到下顺序执行。
    """

    def __init__(self, metadata: MetaData, dialect_name: str) -> None:
        self.metadata = metadata
        self.dialect_name = dialect_name
        self.dialect = DdlDialects.resolve(dialect_name)

    def export(self, *, title: str) -> str:
        """输出完整脚本；title 写入文件头，说明该脚本覆盖的范围。"""
        blocks = [self._header(title)]
        for table in self.metadata.sorted_tables:
            blocks.append(self._table(table))
        return "\n".join(blocks)

    def _header(self, title: str) -> str:
        """文件头声明脚本由模型生成，避免有人直接改 SQL 导致与模型不一致。"""
        return (
            f"-- {title}\n"
            f"-- 数据库方言：{self.dialect_name}\n"
            "-- 本文件由模型导出生成，请勿手工修改；表结构变更请改模型后重新导出。\n"
        )

    def _table(self, table) -> str:
        """输出建表、索引及方言要求独立执行的注释语句。"""
        statements = [str(CreateTable(table).compile(dialect=self.dialect)).strip()]
        if self.dialect_name == "dm":
            # 达梦驱动属于可选依赖（dameng），只在导出达梦 DDL 时导入，不影响其他方言导出。
            from framework.starter_database.ddl.dm_ddl_compiler import DmDdlCompiler

            statements.extend(
                str(
                    AddConstraint(constraint, isolate_from_table=False).compile(
                        dialect=self.dialect
                    )
                ).strip()
                for constraint in DmDdlCompiler.computed_unique_constraints(table)
            )
        for index in sorted(table.indexes, key=lambda item: item.name):
            statements.append(str(CreateIndex(index).compile(dialect=self.dialect)).strip())
        if self.dialect.supports_comments and not self.dialect.inline_comments:
            comments = [SetTableComment(table)] if table.comment is not None else []
            comments.extend(
                SetColumnComment(column) for column in table.columns if column.comment is not None
            )
            statements.extend(
                str(comment.compile(dialect=self.dialect)).strip() for comment in comments
            )
        body = ";\n".join(statements)
        return f"\n-- {table.name}{self._comment(table)}\n{body};\n"

    @staticmethod
    def _comment(table) -> str:
        """表注释附在分隔注释里，方言不支持表注释时也能看到说明。"""
        return f"：{table.comment}" if table.comment else ""
