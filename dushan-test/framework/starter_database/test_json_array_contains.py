import pytest
from sqlalchemy import JSON, Column, Integer, MetaData, Table, create_engine, insert, or_, select
from sqlalchemy.dialects import oracle, sqlite
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.exc import UnsupportedCompilationError

from fixtures.database_fixtures import TARGETS
from framework.starter_database.ddl.ddl_dialects import DdlDialects
from framework.starter_database.model.json_array_contains import JsonArrayContains
from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.dal.dataobject.tenant.tenant_do import TenantDO


@pytest.fixture
def sqlite_arrays():
    metadata = MetaData()
    table = Table(
        "array_members",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("payload", JSON(none_as_null=True)),
    )
    payloads = [
        ["MAIL", "INTERNAL"],
        ["mail"],
        ['a"b'],
        [r"a\b"],
        ["a%b"],
        ["a_b"],
        None,
        JSON.NULL,
        [],
        [""],
        [1, True, False, None, ["MAIL"], {"value": "MAIL"}],
        ["1", "true", "false"],
        ["prefixMAILsuffix"],
        ["aXb"],
        ["a'b --"],
    ]
    engine = create_engine("sqlite://")
    try:
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                insert(table),
                [{"id": index, "payload": payload} for index, payload in enumerate(payloads, 1)],
            )
            yield connection, table
    finally:
        engine.dispose()


class TestJsonArrayContains:
    @pytest.mark.parametrize(
        "database_settings",
        [target for target in TARGETS if target["name"] in {"sqlite", "dm"}],
        indirect=True,
        ids=lambda target: target["name"],
    )
    async def test_runtime_matches_only_equal_strings(self, database_case):
        """真实实例保留字符串类型、大小写与特殊字符，缓存查询必须重新绑定值。"""
        database, item, mapper = database_case
        payloads = [
            ["MAIL", "INTERNAL"],
            ["mail"],
            ['a"b'],
            [r"a\b"],
            ["a%b"],
            ["a_b"],
            None,
            [],
            [""],
            [1, True, False, None, ["MAIL"], {"value": "MAIL"}],
            ["1", "true", "false"],
            ["prefixMAILsuffix"],
            ["aXb"],
            ["a'b --"],
            ["中文😀"],
        ]
        async with database.transaction():
            for index, payload in enumerate(payloads, 1):
                await mapper.insert(item(value=str(index), payload=payload))
        async with database.read_session() as session:
            for value, expected in [
                ("MAIL", ["1"]),
                ("mail", ["2"]),
                ("Mail", []),
                ("AIL", []),
                ('a"b', ["3"]),
                (r"a\b", ["4"]),
                ("a%b", ["5"]),
                ("a_b", ["6"]),
                ("%", []),
                ("_", []),
                ("", ["9"]),
                ("1", ["11"]),
                ("true", ["11"]),
                ("false", ["11"]),
                ("null", []),
                ("a'b --", ["14"]),
                ("中文😀", ["15"]),
                ("MAIL", ["1"]),
            ]:
                statement = select(item.value).where(JsonArrayContains(item.payload, value))
                assert (await session.scalars(statement)).all() == expected, value
            statement = select(item.value).where(
                or_(
                    JsonArrayContains(item.payload, "MAIL"),
                    JsonArrayContains(item.payload, 'a"b'),
                )
            )
            assert set((await session.scalars(statement)).all()) == {"1", "3"}

    @pytest.mark.parametrize("dialect_name", (*DdlDialects.names(), "sqlite"))
    def test_compilation_keeps_string_in_bound_parameter(self, dialect_name):
        """七种注册方言与 SQLite 使用原生 JSON 运算，特殊字符只出现在绑定值中。"""
        dialect = (
            sqlite.dialect() if dialect_name == "sqlite" else DdlDialects.resolve(dialect_name)
        )
        table = Table("array_members", MetaData(), Column("payload", JSON))
        value = "a\"b\\c%_' OR 1=1 --"
        compiled = JsonArrayContains(table.c.payload, value).compile(dialect=dialect)
        mysql_sql = "JSON_CONTAINS(array_members.payload, JSON_QUOTE(%s))"
        postgresql_sql = (
            "(CAST(array_members.payload AS JSONB) @> "
            "CAST(json_build_array(CAST($1::VARCHAR AS TEXT)) AS JSONB))"
        )
        expected = {
            "mysql": mysql_sql,
            "tidb": mysql_sql,
            "oceanbase": mysql_sql,
            "postgresql": postgresql_sql,
            "opengauss": postgresql_sql,
            "kingbase": postgresql_sql,
            "dm": ("COALESCE(JSON_OVERLAPS(array_members.payload, TO_JSON(:param_1)), 0)"),
            "sqlite": (
                "EXISTS (SELECT 1 FROM json_each(array_members.payload) "
                "WHERE json_each.type = 'text' AND json_each.value = ?)"
            ),
        }
        assert str(compiled) == expected[dialect_name]
        assert compiled.params == {"param_1": value}
        assert value not in str(compiled)

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("MAIL", [1]),
            ("INTERNAL", [1]),
            ("missing", []),
            ("mail", [2]),
            ("Mail", []),
            ("AIL", []),
            ('a"b', [3]),
            (r"a\b", [4]),
            ("a%b", [5]),
            ("a_b", [6]),
            ("%", []),
            ("_", []),
            ("", [10]),
            ("1", [12]),
            ("true", [12]),
            ("false", [12]),
            ("null", []),
            ("a'b --", [15]),
        ],
    )
    def test_sqlite_matches_only_equal_string_elements(self, sqlite_arrays, value, expected):
        """只匹配顶层字符串元素，保留大小写和特殊字符且不转换其他 JSON 类型。"""
        connection, table = sqlite_arrays
        statement = (
            select(table.c.id).where(JsonArrayContains(table.c.payload, value)).order_by(table.c.id)
        )
        assert connection.scalars(statement).all() == expected

    def test_sqlite_null_and_empty_array_do_not_match(self, sqlite_arrays):
        """SQL NULL、JSON null 和空数组均不包含任何字符串。"""
        connection, table = sqlite_arrays
        statement = (
            select(JsonArrayContains(table.c.payload, "MAIL"))
            .where(table.c.id.in_([7, 8, 9]))
            .order_by(table.c.id)
        )
        assert connection.scalars(statement).all() == [False, False, False]

    def test_sqlite_combines_channels_with_or(self, sqlite_arrays):
        connection, table = sqlite_arrays
        statement = (
            select(table.c.id)
            .where(
                or_(
                    JsonArrayContains(table.c.payload, "MAIL"),
                    JsonArrayContains(table.c.payload, "INTERNAL"),
                    JsonArrayContains(table.c.payload, 'a"b'),
                )
            )
            .order_by(table.c.id)
        )
        assert connection.scalars(statement).all() == [1, 3]

    def test_sqlite_statement_cache_rebinds_each_value(self, sqlite_arrays):
        """相同结构的缓存语句在连续查询时使用各自的参数。"""
        connection, table = sqlite_arrays
        cache = {}
        connection = connection.execution_options(compiled_cache=cache)
        for value, expected in [("MAIL", [1]), ("mail", [2]), ("MAIL", [1])]:
            statement = select(table.c.id).where(JsonArrayContains(table.c.payload, value))
            assert connection.scalars(statement).all() == expected
        assert len(cache) == 1

    @pytest.mark.parametrize(
        "model, column, value",
        [
            (NoticeDO, NoticeDO.channels, "MAIL"),
            (TenantDO, TenantDO.websites, "https://example.test"),
        ],
        ids=["notice", "tenant"],
    )
    def test_orm_final_froms_supports_permission_inspection(self, model, column, value):
        """权限检查可在没有连接方言时解析包含 JSON 条件的 ORM 查询来源。"""
        statement = select(model).where(JsonArrayContains(column, value))
        assert statement.get_final_froms() == [model.__table__]

    def test_default_compilation_keeps_string_in_bound_parameter(self):
        """离线结构解析使用默认方言时仍保留绑定参数。"""
        value = "a\"b\\c%_' OR 1=1 --"
        compiled = JsonArrayContains(TenantDO.websites, value).compile(dialect=DefaultDialect())
        assert str(compiled) == (
            "(CAST(system_tenant.websites AS JSONB) @> "
            "CAST(json_build_array(CAST(:param_1 AS TEXT)) AS JSONB))"
        )
        assert compiled.params == {"param_1": value}
        assert value not in str(compiled)

    def test_unsupported_dialect_is_not_silently_supported(self):
        table = Table("array_members", MetaData(), Column("payload", JSON))
        with pytest.raises(UnsupportedCompilationError):
            JsonArrayContains(table.c.payload, "MAIL").compile(dialect=oracle.dialect())
