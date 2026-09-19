import asyncio

import dmAsync
from dmSQLAlchemy.dmasync import DMAdaptDBAPI
from sqlalchemy.util import await_only

from framework.common.utils.asyncio_utils import AsyncioUtils
from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_database.dialects.dm_async_connection import DmAsyncConnection


class DmAsyncDbapi(DMAdaptDBAPI):
    """原厂 DPI 连接在线程中创建，完成后交给当前应用事件循环。"""

    def connect(self, *args, **kwargs):
        return DmAsyncConnection(self, await_only(self._connect(*args, **kwargs)))

    @staticmethod
    async def _connect(*args, **kwargs):
        # 原厂方言同时传入 dsn 与 host；dmAsync 明确要求二选一，以完整 dsn 为准。
        if kwargs.get("dsn") is not None:
            kwargs.pop("host", None)
            kwargs.pop("port", None)
        if "database" in kwargs:
            kwargs["schema"] = kwargs.pop("database")
        if kwargs.get("connection_timeout") is None:
            kwargs["connection_timeout"] = 0
        loop = asyncio.get_running_loop()
        task = asyncio.create_task(asyncio.to_thread(dmAsync.connect, *args, loop=loop, **kwargs))
        try:
            return await AsyncioUtils.run_cancellation_shielded(task)
        except asyncio.CancelledError as primary:
            if not task.cancelled() and task.exception() is None:
                connection = task.result()
                error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                    connection.close, "取消达梦连接创建"
                )
                CleanupUtils.raise_collected_cleanup_errors(
                    "达梦连接取消清理失败",
                    [] if error is None else [error],
                    primary_error=primary,
                    caller_cancellation=cancellation,
                )
            raise
