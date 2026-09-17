from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.engine.interfaces import Dialect


class DdlDialects:
    """导出建表语句时可选的数据库方言。

    TiDB 与 OceanBase 使用 MySQL 协议，openGauss 与金仓使用 PostgreSQL 协议，
    因此共用对应方言编译；达梦有独立方言实现，单独注册。
    """

    _FACTORIES = {
        "mysql": mysql.dialect,
        "tidb": mysql.dialect,
        "oceanbase": mysql.dialect,
        "postgresql": postgresql.dialect,
        "opengauss": postgresql.dialect,
        "kingbase": postgresql.dialect,
    }

    @classmethod
    def names(cls) -> tuple[str, ...]:
        return (*sorted(cls._FACTORIES), "dm")

    @classmethod
    def resolve(cls, name: str) -> Dialect:
        """按名称构造方言实例；达梦按需导入，避免未安装驱动时影响其他方言。"""
        if name == "dm":
            from framework.starter_database.dialects.dm_async_dialect import DmAsyncDialect

            return DmAsyncDialect()
        factory = cls._FACTORIES.get(name)
        if factory is None:
            raise ValueError(f"不支持的数据库方言：{name}；可选 {'、'.join(cls.names())}")
        return factory()
