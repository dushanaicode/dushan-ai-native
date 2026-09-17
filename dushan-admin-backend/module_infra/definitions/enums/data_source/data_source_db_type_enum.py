from framework.common.enums.base_enum import BaseEnum


class DataSourceDbTypeEnum(BaseEnum):
    """数据库类型枚举"""

    # 开源数据库
    POSTGRESQL = ("postgresql", "PostgreSQL")
    MYSQL = ("mysql", "MySQL/MariaDB")
    SQLITE = ("sqlite", "SQLite")

    # 商业数据库
    ORACLE = ("oracle", "Oracle")
    MSSQL = ("mssql", "Microsoft SQL Server")

    # 国产数据库（兼容 PostgreSQL 协议，原生异步支持）
    KINGBASE = ("kingbase", "人大金仓 (KingbaseES)")
    HIGHGO = ("highgo", "瀚高数据库 (HighGo DB)")
    GAUSSDB = ("gaussdb", "华为 GaussDB")

    @classmethod
    def get_all_options(cls):
        """获取所有数据库类型选项"""
        return [(item.value, item.label) for item in cls]

    @classmethod
    def get_rdbms_types(cls):
        """获取RDBMS数据库类型"""
        rdbms_types = [
            cls.ORACLE,
            cls.MSSQL,
            cls.POSTGRESQL,
            cls.MYSQL,
            cls.SQLITE,
            cls.KINGBASE,
            cls.HIGHGO,
            cls.GAUSSDB,
        ]
        return [item.value for item in rdbms_types]

    @classmethod
    def is_file_database(cls, db_type: str) -> bool:
        """判断是否为文件数据库"""
        return db_type == cls.SQLITE.value

    @classmethod
    def needs_port(cls, db_type: str) -> bool:
        """判断是否需要端口"""
        return db_type != cls.SQLITE.value

    @classmethod
    def get_default_port(cls, db_type: str) -> int:
        """获取数据库默认端口"""
        port_mapping = {
            cls.MYSQL.value: 3306,
            cls.POSTGRESQL.value: 5432,
            cls.ORACLE.value: 1521,
            cls.MSSQL.value: 1433,
            cls.SQLITE.value: 0,
            cls.KINGBASE.value: 54321,
            cls.HIGHGO.value: 5866,
            cls.GAUSSDB.value: 5432,
        }
        return port_mapping[db_type]

    @classmethod
    def get_driver_info(cls, db_type: str, use_async: bool = True):
        """获取数据库驱动信息"""
        driver_mapping = {
            cls.MYSQL.value: {"async": "aiomysql", "sync": "pymysql"},
            cls.POSTGRESQL.value: {"async": "asyncpg", "sync": "psycopg2"},
            cls.ORACLE.value: {"async": "oracledb", "sync": "cx_oracle"},
            cls.MSSQL.value: {"async": "aioodbc", "sync": "pyodbc"},
            cls.SQLITE.value: {"async": "aiosqlite", "sync": "sqlite3"},
            cls.KINGBASE.value: {"async": "asyncpg", "sync": "psycopg2"},
            cls.HIGHGO.value: {"async": "asyncpg", "sync": "psycopg2"},
            cls.GAUSSDB.value: {"async": "asyncpg", "sync": "psycopg2"},
        }

        driver_type = "async" if use_async else "sync"
        return driver_mapping[db_type][driver_type]

    @classmethod
    def get_sqlalchemy_url_scheme(cls, db_type: str, use_async: bool = True) -> str:
        """
        获取 SQLAlchemy 连接 URL 的 dialect+driver 前缀。

        SQLAlchemy 通过 URL scheme 自动选择数据库方言（Dialect），
        Mapper 层无需关心底层数据库差异。

        说明:
            - KingbaseES / HighGo / GaussDB 兼容 PostgreSQL 协议，复用 postgresql Dialect
        """
        scheme_mapping = {
            cls.MYSQL.value: ("mysql+aiomysql", "mysql+pymysql"),
            cls.POSTGRESQL.value: ("postgresql+asyncpg", "postgresql+psycopg2"),
            cls.ORACLE.value: ("oracle+oracledb", "oracle+cx_oracle"),
            cls.MSSQL.value: ("mssql+aioodbc", "mssql+pyodbc"),
            cls.SQLITE.value: ("sqlite+aiosqlite", "sqlite"),
            cls.KINGBASE.value: ("postgresql+asyncpg", "postgresql+psycopg2"),
            cls.HIGHGO.value: ("postgresql+asyncpg", "postgresql+psycopg2"),
            cls.GAUSSDB.value: ("postgresql+asyncpg", "postgresql+psycopg2"),
        }
        idx = 0 if use_async else 1
        return scheme_mapping[db_type][idx]

    @classmethod
    def build_sqlalchemy_url(
        cls,
        db_type: str,
        host: str,
        port: int,
        database: str,
        username: str = "",
        password: str = "",
        use_async: bool = True,
    ) -> str:
        """
        根据连接参数构建完整的 SQLAlchemy URL。

        Returns:
            格式: dialect+driver://user:pass@host:port/database
        """
        scheme = cls.get_sqlalchemy_url_scheme(db_type, use_async)

        # SQLite 使用文件路径
        if db_type == cls.SQLITE.value:
            return f"{scheme}:///{database}"

        # 有用户名密码
        if username:
            from urllib.parse import quote_plus

            encoded_password = quote_plus(password) if password else ""
            return f"{scheme}://{username}:{encoded_password}@{host}:{port}/{database}"

        return f"{scheme}://{host}:{port}/{database}"
