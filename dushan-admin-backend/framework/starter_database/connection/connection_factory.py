import asyncio

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.config.data_source_settings import DataSourceSettings
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator


class ConnectionFactory:
    """复用 SQLAlchemy 方言加载异步驱动，驱动依赖只在实际启用时导入。"""

    @staticmethod
    def create(source: DataSourceSettings, settings: DatabaseSettings) -> AsyncEngine:
        url = make_url(source.url.get_secret_value())
        dialect = url.get_dialect(_is_async=True)
        if not dialect.is_async:
            raise ValueError("运行时数据源要求 SQLAlchemy 异步方言")
        pool = settings.pool if source.pool is None else source.pool
        options = {"hide_parameters": True, "pool_pre_ping": pool.pre_ping}
        if source.tls is not None:
            if dialect.driver not in {"aiomysql", "asyncpg"}:
                raise ValueError("通用 TLS 配置支持 aiomysql/asyncpg；其他驱动使用其专用连接参数")
            options["connect_args"] = {"ssl": source.tls.create_context()}
        if url.get_backend_name() != "sqlite" or url.database not in (None, "", ":memory:"):
            options.update(
                pool_size=pool.size,
                max_overflow=pool.max_overflow,
                pool_timeout=pool.timeout_seconds,
                pool_recycle=pool.recycle_seconds,
            )
        engine = create_async_engine(url, **options)
        DatabaseErrorTranslator.install(engine.sync_engine)
        if dialect.driver == "aiosqlite":
            event.listen(engine.sync_engine, "handle_error", ConnectionFactory._cancel_sqlite_query)
        return engine

    @staticmethod
    def _cancel_sqlite_query(context) -> None:
        """取消实际 SQLite 查询后再关闭，避免未完成的 RETURNING 游标继续占锁。"""
        if context.connection is None or not isinstance(
            context.original_exception, asyncio.CancelledError
        ):
            return

        async def finish(connection):
            await connection.interrupt()
            # 查询运行在线程中；重复取消不能打断关闭，再由 SQLAlchemy 完成连接失效。
            error, _ = await CleanupUtils.run_cancellation_safe_cleanup(
                connection.close, "关闭已取消查询的 SQLite 连接"
            )
            if error is not None:
                raise context.original_exception from error

        context.connection.connection.dbapi_connection.run_async(finish)

    @staticmethod
    async def probe(engine: AsyncEngine) -> None:
        with DatabaseErrorTranslator.boundary(dialect=engine.dialect, phase="connect"):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))

    @staticmethod
    async def validate_transaction_mode(engine: AsyncEngine) -> None:
        """MySQL 协议必须真正关闭自动提交，避免驱动握手标记错误造成回滚失效。"""
        if engine.dialect.name == "mysql":
            async with engine.connect() as connection:
                if await connection.scalar(text("SELECT @@autocommit")) != 0:
                    raise ValueError(
                        "服务端仍开启自动提交；OceanBase 请使用 oceanbase+aiomysql 方言"
                    )
