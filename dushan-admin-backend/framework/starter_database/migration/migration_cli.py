import argparse
import asyncio
import importlib
import sys
from pathlib import Path

from sqlalchemy import MetaData

from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.migration.migration_runner import MigrationRunner


class MigrationCLI:
    """独立部署作业入口，配置与版本目录均须显式指定，不加载应用启动模块。"""

    @staticmethod
    def parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="显式执行数据库版本迁移，不启动应用")
        parser.add_argument("--config-dir", type=Path, required=True)
        parser.add_argument("--env", choices=["dev", "test", "staging", "prod"])
        parser.add_argument("--source", required=True)
        parser.add_argument("--versions", type=Path, required=True)
        parser.add_argument("--version-table", default="alembic_version")
        parser.add_argument("--metadata", help="结构比较使用的 module:metadata 对象")
        parser.add_argument("--sql", action="store_true", help="只生成离线升级/降级 SQL")
        parser.add_argument(
            "action", choices=["upgrade", "downgrade", "current", "history", "check"]
        )
        parser.add_argument("revision", nargs="?")
        return parser

    @classmethod
    def main(cls) -> int:
        arguments = cls.parser().parse_args()
        try:
            bootstrap = BootstrapConfigProvider.load(arguments.config_dir, app_env=arguments.env)
            configuration = ConfigProvider(bootstrap, (DatabaseSettings,))
            try:
                settings = configuration.get_config(DatabaseSettings)
            finally:
                configuration.close()
            metadata = None
            if arguments.metadata is not None:
                module_name, separator, attribute = arguments.metadata.partition(":")
                if not separator:
                    raise ValueError("metadata 必须使用 module:attribute 格式")
                metadata = getattr(importlib.import_module(module_name), attribute)
                if not isinstance(metadata, MetaData):
                    raise TypeError("metadata 必须引用 SQLAlchemy MetaData 对象")
            runner = MigrationRunner(
                settings,
                source=arguments.source,
                versions=arguments.versions,
                version_table=arguments.version_table,
                metadata=metadata,
            )
            result = asyncio.run(
                runner.run(arguments.action, revision=arguments.revision, sql=arguments.sql)
            )
        except KeyboardInterrupt:
            print("数据库迁移已中断，请核对版本状态；不自动重试。", file=sys.stderr)
            return 130
        except Exception as error:
            # CLI 失败仍保留非零状态，不把驱动原因、SQL 或连接配置输出到终端。
            detail = error.msg if isinstance(error, DatabaseException) else type(error).__name__
            print(f"数据库迁移失败：{detail}；请核对版本状态。", file=sys.stderr)
            return 1
        print(result, end="")
        return 0
