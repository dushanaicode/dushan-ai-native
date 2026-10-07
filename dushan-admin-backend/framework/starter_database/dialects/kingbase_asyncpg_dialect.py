from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg


class KingbaseAsyncpgDialect(PGDialect_asyncpg):
    """KingbaseES PostgreSQL 模式使用服务端协议版本，不解析产品营销版本字符串。"""

    name = "kingbase"
    supports_statement_cache = True

    def _get_server_version_info(self, connection):
        version = connection.connection.driver_connection.get_server_version()
        return version.major, version.minor, version.micro
