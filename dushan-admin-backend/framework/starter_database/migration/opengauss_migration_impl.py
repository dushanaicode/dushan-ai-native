from alembic.ddl.postgresql import PostgresqlImpl


class OpenGaussMigrationImpl(PostgresqlImpl):
    """openGauss PG 模式复用 PostgreSQL 的版本化 DDL 接点。"""

    __dialect__ = "opengauss"
