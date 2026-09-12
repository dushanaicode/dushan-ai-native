import asyncio
from contextvars import Context

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_database.spi.data_source_config_provider import DataSourceConfigProvider
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_di.context.di_task_runner import DiTaskRunner
from framework.starter_di.decorators.components import starter
from framework.starter_di.exception.di_exception import DiException


@starter
class DatabaseStarter:
    """把数据库资源接入应用任务与关闭协调，不负责发现业务类或创建业务表。"""

    def __init__(
        self, database: SessionProvider, tasks: DiTaskRunner, application: ApplicationContext
    ) -> None:
        self.database, self.tasks, self.application = database, tasks, application
        self.database.bind_task_runner(tasks)
        self._loader: DataSourceConfigProvider | None = None
        self._refresh_task: asyncio.Task | None = None
        self._refresh_lock = asyncio.Lock()
        self.last_refresh_error: str | None = None

    async def open(self) -> None:
        await self.database.open()

    async def attach_source_loader(self, loader: DataSourceConfigProvider) -> None:
        """主库已就绪后接入 Infra 快照，再启动应用拥有的周期协调任务。"""
        if self._loader is not None:
            raise RuntimeError("数据源配置提供器只能绑定一次")
        if not self.database.settings.dynamic_enabled:
            raise ValueError("动态数据源未启用")
        if not self.database.is_ready:
            raise RuntimeError("必须在主库就绪后绑定配置提供器")
        self._loader = loader
        await self.refresh_sources()
        self._refresh_task = asyncio.create_task(
            self._refresh_loop(), context=Context(), name="database-source-refresh"
        )

    async def refresh_sources(self, *, preflight=False) -> int:
        if self._loader is None:
            raise RuntimeError("尚未绑定数据源配置提供器")
        async with self._refresh_lock:
            sources = await self._loader.load_sources()
            revision = await self.database.replace_sources(sources, preflight=preflight)
            self.last_refresh_error = None
            return revision

    async def _refresh_loop(self):
        await self.application.wait_until_ready()
        while self.application.state is ApplicationStateEnum.READY:
            await asyncio.sleep(self.database.settings.dynamic_refresh_interval_seconds)
            try:
                await self.tasks.run(self.refresh_sources)
            except DiException:
                if self.application.state is not ApplicationStateEnum.READY:
                    return
                raise
            except (DatabaseException, SQLAlchemyError, OSError, TimeoutError, ValueError) as error:
                self.last_refresh_error = type(error).__name__
                logger.error("动态数据库刷新失败，保留上次快照：{}", self.last_refresh_error)

    async def close(self) -> None:
        errors = []
        if self.application.state is ApplicationStateEnum.STARTING:
            self.database._transactions.cancel_callbacks()
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            except BaseException as error:
                errors.append(error)
            self._refresh_task = None
        try:
            await self.database.close()
        except BaseException as error:
            errors.append(error)
        CleanupUtils.raise_collected_cleanup_errors("数据库 Starter 关闭失败", errors)
