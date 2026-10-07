from uuid import uuid4

import pytest
from sqlalchemy import JSON, Column, Integer, MetaData, Table, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateTable

from fixtures.database_fixtures import TARGETS
from framework.starter_database.ddl.ddl_dialects import DdlDialects
from module_system.dal.dataobject.social.social_client_do import SocialClientDO


class TestJsonDefaults:
    @pytest.mark.parametrize(
        "database_settings",
        [target for target in TARGETS if target["name"] in {"sqlite", "dm"}],
        indirect=True,
        ids=lambda target: target["name"],
    )
    async def test_runtime_empty_object_default_and_not_null(self, database_settings):
        """裸 SQL 省略 JSON 列时由数据库生成空对象，显式 NULL 仍违反非空约束。"""
        table = Table(
            "json_defaults_" + uuid4().hex[:16],
            MetaData(),
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column(
                "payload",
                JSON,
                nullable=False,
                server_default=SocialClientDO.__table__.c.auth_config.server_default.arg,
            ),
        )
        engine = create_async_engine(database_settings.sources[0].url.get_secret_value())
        created = False
        try:
            async with engine.begin() as connection:
                await connection.run_sync(table.create)
            created = True
            async with engine.begin() as connection:
                await connection.exec_driver_sql(f"INSERT INTO {table.name} (id) VALUES (1)")
                assert await connection.scalar(select(table.c.payload)) == {}
            with pytest.raises(IntegrityError):
                async with engine.begin() as connection:
                    await connection.exec_driver_sql(
                        f"INSERT INTO {table.name} (id, payload) VALUES (2, NULL)"
                    )
        finally:
            try:
                if created:
                    async with engine.begin() as connection:
                        await connection.run_sync(table.drop)
            finally:
                await engine.dispose()

    @pytest.mark.parametrize("dialect_name", DdlDialects.names())
    def test_empty_object_default_preserves_database_semantics(self, dialect_name):
        """按数据库能力生成空 JSON 默认值，避免 TiDB 和 OceanBase 拒绝建表。"""
        dialect = DdlDialects.resolve(dialect_name)
        default = SocialClientDO.__table__.c.auth_config.server_default.arg
        mysql_family = dialect_name in {"mysql", "tidb", "oceanbase"}
        expected = "(JSON_OBJECT())" if mysql_family else "'{}'"
        assert str(default.compile(dialect=dialect)) == expected
        ddl = str(CreateTable(SocialClientDO.__table__).compile(dialect=dialect))
        if dialect_name == "oceanbase":
            column_ddl = next(line for line in ddl.splitlines() if "auth_config " in line)
            assert "NOT NULL" in column_ddl
            assert "DEFAULT" not in column_ddl
        else:
            assert f"DEFAULT {expected}" in ddl
        assert "DEFAULT ('{}')" not in ddl
