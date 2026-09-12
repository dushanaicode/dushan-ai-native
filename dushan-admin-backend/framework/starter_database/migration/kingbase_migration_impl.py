from alembic.ddl.postgresql import PostgresqlImpl


class KingbaseMigrationImpl(PostgresqlImpl):
    """金仓 PG 模式沿用 PostgreSQL 迁移语法。"""

    __dialect__ = "kingbase"
