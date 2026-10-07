from contextlib import asynccontextmanager

from sqlalchemy import inspect

from framework.starter_database.public import (
    ConnectionFactory,
    DatabaseSettings,
    DataSourceSettings,
)
from framework.starter_di.public import (
    Inject,
    util,
)
from module_infra.util.codegen.codegen_type_utils import CodegenTypeUtils


@util
class DbSchemaUtils:
    settings: DatabaseSettings = Inject()

    @asynccontextmanager
    async def _connection(self, config):
        """读取元数据的连接随临时引擎释放，主错误和取消由框架保留。"""
        source = DataSourceSettings(
            name="schema_reader", url=config.url, role="named", weight=100, pool=None, tls=None
        )
        async with ConnectionFactory.temporary_engine(source, self.settings) as engine:
            async with engine.connect() as connection:
                yield connection

    @staticmethod
    def _comment(inspector, name):
        try:
            return inspector.get_table_comment(name)["text"] or ""
        except NotImplementedError:
            return ""

    async def get_table_list(self, config, table_name=None, table_comment=None):
        async with self._connection(config) as connection:
            rows = await connection.run_sync(self._tables)
        return [
            row
            for row in rows
            if (not table_name or table_name.lower() in row["name"].lower())
            and (not table_comment or table_comment.lower() in row["comment"].lower())
        ]

    def _tables(self, connection):
        inspector = inspect(connection)
        return [
            {"name": name, "comment": self._comment(inspector, name)}
            for name in inspector.get_table_names()
        ]

    async def get_table_comment(self, config, table_name):
        async with self._connection(config) as connection:
            return await connection.run_sync(lambda conn: self._comment(inspect(conn), table_name))

    async def get_table_columns(self, config, table_name):
        async with self._connection(config) as connection:
            return await connection.run_sync(self._columns, table_name)

    @staticmethod
    def _columns(connection, table_name):
        inspector = inspect(connection)
        primary = inspector.get_pk_constraint(table_name)["constrained_columns"]
        return [
            {
                "column_name": column["name"],
                "column_comment": column.get("comment") or "",
                **CodegenTypeUtils.metadata(column["type"]),
                "column_type": str(column["type"]),
                "is_nullable": column["nullable"],
                "column_key": "PRI" if column["name"] in primary else "",
                "ordinal_position": index + 1,
                "computed_expression": column.get("computed", {}).get("sqltext"),
                "computed_persisted": column.get("computed", {}).get("persisted"),
            }
            for index, column in enumerate(inspector.get_columns(table_name))
        ]
