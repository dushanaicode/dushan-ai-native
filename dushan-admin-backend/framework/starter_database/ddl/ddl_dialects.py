from sqlalchemy.dialects import registry
from sqlalchemy.engine.interfaces import Dialect


class DdlDialects:
    """导出建表语句时可选的数据库方言。

    与数据库连接使用同一注册方言；TiDB 按支持契约使用 MySQL 方言。
    国产方言按需加载，导出其他数据库时不要求安装其专用驱动。
    """

    _PLUGINS = {
        "mysql": "mysql.aiomysql",
        "tidb": "mysql.aiomysql",
        "oceanbase": "oceanbase.aiomysql",
        "postgresql": "postgresql.asyncpg",
        "opengauss": "opengauss.asyncpg",
        "kingbase": "kingbase.asyncpg",
        "dm": "dm.dushan_async",
    }

    @classmethod
    def names(cls) -> tuple[str, ...]:
        """列出可导出的数据库名称。"""
        return tuple(sorted(cls._PLUGINS))

    @classmethod
    def resolve(cls, name: str) -> Dialect:
        """按名称构造方言实例；达梦按需导入，避免未安装驱动时影响其他方言。"""
        if name not in cls._PLUGINS:
            raise ValueError(f"不支持的数据库方言：{name}；可选 {'、'.join(cls.names())}")
        dialect = registry.load(cls._PLUGINS[name])()
        if name == "opengauss":
            dialect.supports_identity_columns = False
        return dialect
