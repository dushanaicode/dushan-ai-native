import asyncio

from dmSQLAlchemy.dmasync import AsyncAdapt_dmasync_cursor

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils


class DmAsyncCursor(AsyncAdapt_dmasync_cursor):
    """为当前 dmSQLAlchemy 的游标补齐被类属性遮蔽的 SQLAlchemy 存储槽。"""

    __slots__ = ("_cursor",)

    def execute(self, operation, parameters=None):
        """dmAsync 内部使用线程，取消必须等待实际查询结束后再交还连接。"""
        return self._execute_buffered(operation, parameters)

    async def _execute_buffered(self, operation, parameters):
        await AsyncioUtils.run_cancellation_shielded(self._cursor.execute(operation, parameters))
        if self._cursor.description and not self.server_side:
            rows = await AsyncioUtils.run_cancellation_shielded(
                asyncio.to_thread(self._cursor.raw.fetchall)
            )
            self._rows.extend(rows)

    def fetchall(self):
        rows = list(self._rows)
        self._rows.clear()
        return rows

    def fetchone(self):
        return self._rows.popleft() if self._rows else None

    def executemany(self, operation, parameters):
        """保留 dmPython 的批量输出参数，并等线程结束后再传播取消。"""
        return AsyncioUtils.run_cancellation_shielded(
            asyncio.to_thread(self._cursor.raw.executemany, operation, parameters)
        )
