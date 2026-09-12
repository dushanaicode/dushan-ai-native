from dmSQLAlchemy.dmasync import AsyncAdapt_dmasync_connection

from framework.starter_database.dialects.dm_async_cursor import DmAsyncCursor


class DmAsyncConnection(AsyncAdapt_dmasync_connection):
    """当前 dmSQLAlchemy 2.0.17 在 SQLAlchemy 2.0.52 上的连接存储适配。"""

    __slots__ = ("_connection",)

    def cursor(self):
        return DmAsyncCursor(self)
