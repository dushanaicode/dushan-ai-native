import pytest
from sqlalchemy import Column, Index, Integer, MetaData, Table
from sqlalchemy.dialects import registry
from sqlalchemy.schema import SetColumnComment, SetTableComment

from framework.starter_database.ddl.ddl_dialects import DdlDialects
from framework.starter_database.ddl.ddl_exporter import DdlExporter


@pytest.mark.parametrize("name", DdlDialects.names())
def test_export_preserves_table_and_column_comments(name):
    """内联和独立注释都保留中文、单引号及需引用的标识符。"""
    metadata = MetaData()
    table = Table(
        "order",
        metadata,
        Column("select", Integer, comment="编号'说明"),
        Column("plain", Integer),
        comment="表'说明",
        schema="sample",
    )
    Index("ix_order_plain", table.c.plain)
    exporter = DdlExporter(metadata, name)
    script = exporter.export(title="注释导出验证")
    assert "编号''说明" in script
    assert "表''说明" in script
    assert "CREATE INDEX" in script
    if exporter.dialect.inline_comments:
        assert "COMMENT ON" not in script
        assert "ALTER TABLE" not in script
    else:
        table_comment = str(SetTableComment(table).compile(dialect=exporter.dialect))
        column_comment = str(SetColumnComment(table.c.select).compile(dialect=exporter.dialect))
        assert script.count(table_comment + ";") == 1
        assert script.count(column_comment + ";") == 1
        assert script.index("CREATE TABLE") < script.index(table_comment)
        assert script.count("COMMENT ON COLUMN") == 1


@pytest.mark.parametrize("name", DdlDialects.names())
def test_export_omits_unspecified_comments(name):
    """没有声明注释时不生成空的注释语句。"""
    metadata = MetaData()
    Table("sample", metadata, Column("id", Integer))
    script = DdlExporter(metadata, name).export(title="无注释表")
    assert "COMMENT" not in script


@pytest.mark.parametrize(
    ("name", "plugin"),
    [
        ("mysql", "mysql.aiomysql"),
        ("tidb", "mysql.aiomysql"),
        ("oceanbase", "oceanbase.aiomysql"),
        ("postgresql", "postgresql.asyncpg"),
        ("opengauss", "opengauss.asyncpg"),
        ("kingbase", "kingbase.asyncpg"),
        ("dm", "dm.dushan_async"),
    ],
)
def test_export_uses_registered_database_dialect(name, plugin):
    """导出与实际连接使用同一注册方言，TiDB 按契约使用 MySQL。"""
    assert type(DdlDialects.resolve(name)) is registry.load(plugin)
