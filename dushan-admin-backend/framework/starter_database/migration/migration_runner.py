import asyncio
import importlib
import io
import re
from pathlib import Path
from typing import Literal

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData
from sqlalchemy.engine import make_url

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.connection.connection_factory import ConnectionFactory
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator


class MigrationRunner:
    """显式运行 Alembic 版本脚本，不创建应用、DI、监控或业务 Session。

    versions 是业务自己的版本脚本目录，version_table 隔离该迁移历史。
    upgrade/downgrade 只执行版本图中所需的迁移，不自动创建业务元数据。
    MySQL/DM 等数据库的 DDL 可能自动提交；失败时不得自动重试或伪称已回滚。
    调用方负责单一部署迁移作业，不从每个 worker 并发调用本入口。
    """

    def __init__(
        self,
        settings: DatabaseSettings,
        *,
        source: str,
        versions: Path,
        version_table: str = "alembic_version",
        metadata: MetaData | None = None,
    ) -> None:
        selected = next((item for item in settings.sources if item.name == source), None)
        if selected is None or selected.role == "replica":
            raise ValueError("迁移要求明确的 primary 或 named 数据源")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", version_table):
            raise ValueError("迁移版本表名称必须为合法的小写标识符")
        if not versions.is_dir():
            raise ValueError("迁移版本目录必须已存在")
        self.settings, self.source = settings, selected
        self.versions = versions.resolve()
        self.version_table, self.metadata = version_table, metadata

    def _configuration(self, output: io.StringIO) -> Config:
        config = Config(stdout=output, output_buffer=output)
        location = Path(__file__).with_name("environment")
        config.set_main_option("script_location", str(location).replace("%", "%%"))
        config.set_main_option("path_separator", "os")
        config.set_main_option("version_locations", str(self.versions).replace("%", "%%"))
        config.attributes.update(
            target_metadata=self.metadata,
            version_table=self.version_table,
        )
        return config

    @staticmethod
    def _register_dialect(name: str) -> None:
        modules = {
            "kingbase": "kingbase_migration_impl",
            "opengauss": "opengauss_migration_impl",
            "dm": "dm_migration_impl",
        }
        if name in modules:
            importlib.import_module(f"framework.starter_database.migration.{modules[name]}")

    async def run(
        self,
        action: Literal["upgrade", "downgrade", "current", "history", "check"],
        *,
        revision: str | None = None,
        sql: bool = False,
    ) -> str:
        """执行显式命令；sql=True 只输出版本 SQL，不连接数据库。"""
        if action not in {"upgrade", "downgrade", "current", "history", "check"}:
            raise ValueError("未知迁移命令")
        if action in {"upgrade", "downgrade"} and not revision:
            raise ValueError("升级或降级必须明确指定目标版本")
        if sql and action not in {"upgrade", "downgrade"}:
            raise ValueError("只有升级或降级可以输出离线 SQL")
        if action == "check" and self.metadata is None:
            raise ValueError("比较模型结构需要显式传入 MetaData")
        output = io.StringIO()
        config = self._configuration(output)
        if action == "history":
            command.history(config, verbose=True)
            return output.getvalue()
        url = make_url(self.source.url.get_secret_value())
        dialect_class = url.get_dialect(_is_async=True)
        self._register_dialect(dialect_class.name)
        if sql:
            config.attributes["dialect_name"] = url.drivername
            self._execute(config, action, revision, sql=True)
            return output.getvalue()
        engine = ConnectionFactory.create(self.source, self.settings)
        primary = None
        connection = None
        try:
            with DatabaseErrorTranslator.boundary(dialect=engine.dialect, phase="migration"):
                async with asyncio.timeout(self.settings.connect_timeout_seconds):
                    connection = await engine.connect()
                await connection.run_sync(self._online, config, action, revision)
        except BaseException as error:
            primary = DatabaseErrorTranslator.translate(
                error, dialect=engine.dialect, phase="migration"
            )
        finally:
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                lambda: self._release(connection, engine), "独立迁移连接释放"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "数据库迁移失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
        return output.getvalue()

    @staticmethod
    async def _release(connection, engine) -> None:
        errors = []
        if connection is not None:
            try:
                await connection.close()
            except BaseException as error:
                errors.append(
                    DatabaseErrorTranslator.translate(error, dialect=engine.dialect, phase="close")
                )
        try:
            await engine.dispose()
        except BaseException as error:
            errors.append(
                DatabaseErrorTranslator.translate(error, dialect=engine.dialect, phase="close")
            )
        CleanupUtils.raise_collected_cleanup_errors("迁移连接关闭失败", errors)

    @staticmethod
    def _online(connection, config: Config, action: str, revision: str | None) -> None:
        config.attributes["connection"] = connection
        MigrationRunner._execute(config, action, revision, sql=False)

    @staticmethod
    def _execute(config: Config, action: str, revision: str | None, *, sql: bool) -> None:
        match action:
            case "upgrade":
                command.upgrade(config, revision, sql=sql)
            case "downgrade":
                command.downgrade(config, revision, sql=sql)
            case "current":
                command.current(config)
            case "check":
                command.check(config)
