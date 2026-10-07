import ast
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import (
    BINARY,
    CHAR,
    JSON,
    NCHAR,
    NVARCHAR,
    TIMESTAMP,
    VARBINARY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Enum,
    Float,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    Unicode,
    UnicodeText,
    Uuid,
)
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.exc import CompileError

from module_infra.controller.admin.codegen.vo.codegen_create_list_req_vo import (
    CodegenCreateListReqVO,
)
from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.service.codegen.codegen_service_impl import CodegenServiceImpl
from module_infra.util.codegen import db_schema_utils
from module_infra.util.codegen.codegen_builder_utils import CodegenBuilderUtils
from module_infra.util.codegen.codegen_engine_utils import CodegenEngineUtils
from module_infra.util.codegen.codegen_type_utils import CodegenTypeUtils
from module_infra.util.codegen.db_schema_utils import DbSchemaUtils

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "sql_type,data_type,sql,python_type",
    [
        (Numeric(12, 2), "decimal", "NUMERIC(12, 2)", "Decimal"),
        (mysql.DECIMAL(24, 9), "decimal", "NUMERIC(24, 9)", "Decimal"),
        (Numeric(12, 0), "decimal", "NUMERIC(12, 0)", "Decimal"),
        (postgresql.NUMERIC(), "decimal", "NUMERIC", "Decimal"),
        (String(512), "varchar", "VARCHAR(512)", "str"),
        (CHAR(7), "char", "CHAR(7)", "str"),
        (Unicode(64), "unicode", "VARCHAR(64)", "str"),
        (mysql.NCHAR(8), "nchar", "NATIONAL CHAR(8)", "str"),
        (mysql.NVARCHAR(8), "nvarchar", "NATIONAL VARCHAR(8)", "str"),
        (Text(), "text", "TEXT", "str"),
        (mysql.LONGTEXT(), "longtext", "LONGTEXT", "str"),
        (mysql.MEDIUMTEXT(), "mediumtext", "MEDIUMTEXT", "str"),
        (UnicodeText(), "ntext", "TEXT", "str"),
        (mysql.INTEGER(), "int", "INTEGER", "int"),
        (mysql.TINYINT(), "tinyint", "TINYINT", "int"),
        (BigInteger(), "bigint", "BIGINT", "int"),
        (SmallInteger(), "smallint", "SMALLINT", "int"),
        (Float(24), "float", "FLOAT(24)", "float"),
        (Double(), "double", "DOUBLE", "float"),
        (Boolean(), "boolean", "BOOL", "bool"),
        (mysql.BIT(1), "bit", "BIT(1)", "bool"),
        (Date(), "date", "DATE", "date"),
        (postgresql.TIMESTAMP(), "timestamp", "TIMESTAMP", "datetime"),
        (Time(), "time", "TIME", "time"),
        (JSON(), "json", "JSON", "json"),
        (BINARY(8), "binary", "BINARY(8)", "bytes"),
        (VARBINARY(16), "varbinary", "VARBINARY(16)", "bytes"),
        (mysql.LONGBLOB(), "longblob", "LONGBLOB", "bytes"),
    ],
)
def test_reflected_type_roundtrip_keeps_parameters(sql_type, data_type, sql, python_type):
    """真实 SQLAlchemy 方言类型经过持久化字段后，DO 与 SQL 使用相同精度和容量。"""
    metadata = CodegenTypeUtils.metadata(sql_type)
    column = CodegenColumnDO(**metadata, field_type=CodegenTypeUtils.field_type(data_type))
    assert column.data_type == data_type
    assert column.field_type == python_type
    assert CodegenTypeUtils.sql_expression(column) == sql
    expression = CodegenTypeUtils.python_expression(column)
    namespace = {
        type_class.__name__: type_class
        for type_class in (
            BigInteger,
            SmallInteger,
            Integer,
            Numeric,
            Float,
            Double,
            Boolean,
            String,
            CHAR,
            Text,
            Unicode,
            UnicodeText,
            Date,
            DateTime,
            Time,
            JSON,
            LargeBinary,
            BINARY,
            VARBINARY,
            NCHAR,
            NVARCHAR,
            TIMESTAMP,
        )
    }
    namespace["mysql"] = mysql
    generated = eval(expression, namespace)
    assert str(generated.compile(dialect=mysql.dialect())) == sql
    assert generated.python_type is CodegenTypeUtils.sqlalchemy_type(column).python_type
    if isinstance(sql_type, Numeric) and not isinstance(sql_type, Float):
        assert (generated.precision, generated.scale) == (sql_type.precision, sql_type.scale)


@pytest.mark.parametrize(
    "sql_type",
    [
        Enum("enabled", "disabled"),
        postgresql.ARRAY(Integer()),
        Uuid(),
        mysql.BIT(8),
        mysql.INTEGER(unsigned=True),
        DateTime(timezone=True),
        mysql.DATETIME(fsp=6),
        mysql.FLOAT(precision=12, scale=4),
        mysql.DOUBLE(precision=12, scale=5),
        postgresql.JSONB(),
        postgresql.TIMESTAMP(precision=4),
        postgresql.TIME(precision=3),
        mysql.REAL(),
        postgresql.CITEXT(),
    ],
)
def test_unsupported_reflection_is_rejected(sql_type):
    """不能重建的类型和选项明确失败，不偷偷丢失数据库语义。"""
    with pytest.raises(ValueError, match="代码生成"):
        CodegenTypeUtils.metadata(sql_type)


@pytest.mark.parametrize(
    "sql_type",
    [
        mysql.VARCHAR(length=64, collation="utf8mb4_unicode_ci"),
        mysql.VARCHAR(length=64, charset="utf8mb4"),
        mysql.CHAR(length=8, binary=True),
    ],
)
def test_storage_options_follow_project_convention(sql_type):
    """排序规则与字符集不影响生成语义，按项目建表约定处理而不拒绝。"""
    metadata = CodegenTypeUtils.metadata(sql_type)
    assert (metadata["data_type"], metadata["column_size"]) == (
        "char" if isinstance(sql_type, mysql.CHAR) else "varchar",
        sql_type.length,
    )


@pytest.mark.parametrize(
    "data_type", ["enum", "set", "year", "uuid", "unknown", "numeric", "integer"]
)
def test_unknown_saved_type_is_not_guessed_as_string(data_type):
    """旧元数据中的未支持类型也不会退回字符串生成。"""
    with pytest.raises(ValueError, match="不支持数据库类型"):
        CodegenBuilderUtils.map_field_type(data_type)
    with pytest.raises(ValueError, match="不支持数据库类型"):
        CodegenEngineUtils.computed_type(CodegenColumnDO(data_type=data_type))


def test_varchar_without_length_does_not_invent_a_limit():
    """缺失长度时不擅自填 255，目标 MySQL 的编译器明确拒绝。"""
    column = CodegenColumnDO(
        data_type="varchar", column_size=None, field_type="str", type_metadata_synced=True
    )
    assert CodegenEngineUtils.computed_type(column) == "String()"
    with pytest.raises(CompileError, match="requires a length"):
        CodegenTypeUtils.sql_expression(column)


@pytest.mark.parametrize("synced", [False, None])
def test_unsynchronized_metadata_is_rejected_before_generation(synced):
    """旧元数据缺少精度时必须先同步，不能当成真实的无界 Numeric。"""
    column = CodegenColumnDO(
        column_name="id",
        field_name="id",
        primary_key=True,
        data_type="decimal",
        field_type="Decimal",
        numeric_precision=None,
        numeric_scale=None,
        type_metadata_synced=synced,
    )
    table = CodegenTableDO(
        table_name="billing_invoice",
        module_name="billing",
        business_name="invoice",
        class_name="Invoice",
        template_type=1,
        front_type=0,
    )
    with pytest.raises(ValueError, match="先从数据库同步"):
        CodegenEngineUtils().generate(table, [column])


def test_schema_reader_extracts_type_metadata_without_parsing_labels(monkeypatch):
    """元数据读取直接保留 SQLAlchemy 类型参数及生成列信息。"""
    inspector = SimpleNamespace(
        get_pk_constraint=lambda _: {"constrained_columns": ["id"]},
        get_columns=lambda _: [
            {"name": "id", "type": mysql.BIGINT(), "nullable": False},
            {"name": "amount", "type": mysql.DECIMAL(12, 2), "nullable": False},
            {"name": "body", "type": mysql.LONGTEXT(), "nullable": True},
            {
                "name": "total",
                "type": Numeric(18, 5),
                "nullable": True,
                "computed": {"sqltext": "amount * 2", "persisted": True},
            },
        ],
    )
    monkeypatch.setattr(db_schema_utils, "inspect", lambda _: inspector)
    columns = {row["column_name"]: row for row in DbSchemaUtils._columns(object(), "invoice")}
    assert columns["id"]["column_key"] == "PRI"
    assert columns["amount"]["numeric_precision"] == 12
    assert columns["amount"]["numeric_scale"] == 2
    assert columns["body"]["data_type"] == "longtext"
    assert columns["total"]["computed_expression"] == "amount * 2"
    assert columns["total"]["numeric_precision"] == 18


@pytest.mark.parametrize("template", [1, 2, 15])
def test_main_and_child_templates_share_physical_types(template):
    """三种模板的普通列、生成列和子表保持金额精度与长文本类型。"""
    table = CodegenTableDO(
        id=1,
        table_name="billing_invoice",
        module_name="billing",
        business_name="invoice",
        class_name="Invoice",
        class_comment="账单",
        table_comment="账单",
        template_type=template,
        front_type=0,
        enable_export=False,
    )
    columns = [
        CodegenColumnDO(
            id=1,
            column_name="id",
            field_name="id",
            data_type="bigint",
            field_type="int",
            column_comment="编号",
            primary_key=True,
            nullable=False,
            type_metadata_synced=True,
        ),
        CodegenColumnDO(
            id=2,
            column_name="amount",
            field_name="amount",
            data_type="decimal",
            column_comment="金额",
            numeric_precision=12,
            numeric_scale=2,
            field_type="Decimal",
            nullable=False,
            type_metadata_synced=True,
        ),
        CodegenColumnDO(
            id=3,
            column_name="body",
            field_name="body",
            data_type="longtext",
            column_comment="正文",
            field_type="str",
            nullable=True,
            type_metadata_synced=True,
        ),
        CodegenColumnDO(
            id=4,
            column_name="total",
            field_name="total",
            data_type="decimal",
            column_comment="合计",
            numeric_precision=18,
            numeric_scale=5,
            field_type="Decimal",
            nullable=True,
            computed_expression="amount * 2",
            computed_persisted=True,
            type_metadata_synced=True,
        ),
    ]
    sub_tables = []
    if template == 15:
        child = CodegenTableDO(
            id=2,
            table_name="billing_line",
            module_name="billing",
            business_name="line",
            class_name="Line",
            class_comment="账单明细",
        )
        sub_tables.append({"table": child, "columns": columns, "sub_join_column": None})
    files = CodegenEngineUtils().generate(table, columns, sub_tables)
    models = [item["code"] for item in files if item["filePath"].endswith("_do.py")]
    assert len(models) == (2 if template == 15 else 1)
    for code in models:
        ast.parse(code)
        assert "Numeric(precision=12, scale=2)" in code
        assert "Numeric(precision=18, scale=5)" in code
        assert 'Text().with_variant(mysql.LONGTEXT(), "mysql")' in code
        assert "String(255)" not in code and "18,4" not in code
    sql = next(item["code"] for item in files if item["filePath"].endswith("_table.sql"))
    assert "`amount` NUMERIC(12, 2) NOT NULL" in sql
    assert "`body` LONGTEXT DEFAULT NULL" in sql
    assert "`total` NUMERIC(18, 5) GENERATED ALWAYS" in sql


@pytest.mark.parametrize("existing", [False, True])
async def test_sync_and_import_preserve_numeric_parameters(existing):
    """导入和同步都保存精度；旧列同步时保留用户配置并更新物理类型参数。"""
    db_column = {
        "column_name": "amount",
        "column_comment": "金额",
        "data_type": "decimal",
        "column_size": None,
        "numeric_precision": 24,
        "numeric_scale": 9,
        "column_key": "",
        "is_nullable": False,
        "computed_expression": None,
        "computed_persisted": None,
        "type_metadata_synced": True,
    }
    table = CodegenTableDO(id=1, table_name="billing_invoice", data_source_config_id=1)
    column = CodegenColumnDO(
        id=2,
        column_name="amount",
        data_type="decimal",
        field_type="Decimal",
        numeric_precision=12,
        numeric_scale=2,
        column_comment="用户说明",
        field_name="amount",
    )
    service = CodegenServiceImpl()
    service.data_source_config_service = SimpleNamespace(
        get_data_source_config=AsyncMock(return_value=object())
    )
    service.db_schema_reader = SimpleNamespace(
        get_table_columns=AsyncMock(return_value=[db_column]),
        get_table_comment=AsyncMock(return_value=""),
    )
    service.codegen_table_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=table),
        select_by_table_name_and_data_source=AsyncMock(return_value=None),
        insert=AsyncMock(),
    )
    service.codegen_column_mapper = SimpleNamespace(
        select_list_by_table_id=AsyncMock(return_value=[column] if existing else []),
        update_by_id=AsyncMock(),
        insert=AsyncMock(),
    )
    if existing:
        await CodegenServiceImpl.sync_codegen_from_db.__wrapped__(service, 1)
        service.codegen_column_mapper.update_by_id.assert_awaited_once_with(column)
        assert column.column_comment == "用户说明"
    else:
        req = CodegenCreateListReqVO(data_source_config_id="1", table_names=["billing_invoice"])
        await CodegenServiceImpl.create_codegen_list.__wrapped__(service, req)
        (column,) = service.codegen_column_mapper.insert.await_args.args
    assert (column.data_type, column.numeric_precision, column.numeric_scale) == (
        "decimal",
        24,
        9,
    )
    assert column.type_metadata_synced is True
