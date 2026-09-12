import asyncio

from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.sql.elements import TextClause

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator


class ExternalDatabaseOperator:
    """独立外部库的有界查询，供连接测试/元数据读取使用，不发布 Engine。

    原始 SQL 的权限和允许的数据源由调用入口负责；不借用业务受管 Session。
    同步驱动在线程内完成查询及关闭，调用取消仍等待线程真实退出。
    """

    @classmethod
    async def test_connection(cls, url: SecretStr, *, timeout_seconds: float) -> None:
        await cls.fetch_all(url, text("SELECT 1"), {}, max_rows=1, timeout_seconds=timeout_seconds)

    @classmethod
    async def fetch_all(
        cls,
        url: SecretStr,
        statement: TextClause,
        parameters: dict,
        *,
        max_rows: int,
        timeout_seconds: float,
    ) -> list[tuple]:
        if max_rows < 1 or timeout_seconds <= 0:
            raise ValueError("外部查询的条数和超时必须为正")
        parsed = make_url(url.get_secret_value())
        with DatabaseErrorTranslator.boundary(dialect=parsed.get_backend_name()):
            if parsed.get_dialect(_is_async=True).is_async:
                engine = create_async_engine(parsed, poolclass=NullPool, hide_parameters=True)
                DatabaseErrorTranslator.install(engine.sync_engine)
                primary = None
                try:
                    async with asyncio.timeout(timeout_seconds):
                        async with engine.connect() as connection:
                            result = await connection.execute(statement, parameters)
                            return cls._rows(result, max_rows)
                except BaseException as error:
                    primary = DatabaseErrorTranslator.translate(error, dialect=engine.dialect)
                finally:
                    error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                        engine.dispose, "外部数据库关闭"
                    )
                    CleanupUtils.raise_collected_cleanup_errors(
                        "外部数据库清理失败",
                        []
                        if error is None
                        else [
                            DatabaseErrorTranslator.translate(
                                error, dialect=engine.dialect, phase="close"
                            )
                        ],
                        primary_error=primary,
                        caller_cancellation=cancellation,
                    )
            task = asyncio.create_task(
                asyncio.to_thread(cls._fetch_sync, parsed, statement, parameters, max_rows)
            )
            async with asyncio.timeout(timeout_seconds):
                return await AsyncioUtils.run_cancellation_shielded(task)

    @staticmethod
    def _fetch_sync(url, statement, parameters, max_rows):
        engine = create_engine(url, poolclass=NullPool, hide_parameters=True)
        DatabaseErrorTranslator.install(engine)
        with DatabaseErrorTranslator.boundary(dialect=engine.dialect):
            primary = None
            try:
                with engine.connect() as connection:
                    return ExternalDatabaseOperator._rows(
                        connection.execute(statement, parameters), max_rows
                    )
            except BaseException as error:
                primary = DatabaseErrorTranslator.translate(error, dialect=engine.dialect)
            finally:
                errors = []
                try:
                    engine.dispose()
                except BaseException as error:
                    errors.append(
                        DatabaseErrorTranslator.translate(
                            error, dialect=engine.dialect, phase="close"
                        )
                    )
                CleanupUtils.raise_collected_cleanup_errors(
                    "外部数据库清理失败", errors, primary_error=primary
                )

    @staticmethod
    def _rows(result, max_rows):
        rows = result.fetchmany(max_rows + 1)
        if len(rows) > max_rows:
            raise ValueError("外部查询超过明确的最大返回条数")
        return [tuple(row) for row in rows]
