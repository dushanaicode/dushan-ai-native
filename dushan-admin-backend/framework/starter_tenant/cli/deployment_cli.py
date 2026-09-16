import argparse
import asyncio
import importlib
import json
import sys
from pathlib import Path

from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_tenant.config.tenant_settings import TenantSettings
from framework.starter_tenant.core.deployment_mode_store import DeploymentModeStore


class DeploymentCLI:
    """停止业务进程后显式切换封存记录，不启动 Web、不迁移表结构。"""

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description="显式变更租户部署封存；先停止业务进程")
        parser.add_argument("--config-dir", type=Path, required=True)
        parser.add_argument("--target-config-dir", type=Path, required=True)
        parser.add_argument("--env", choices=("dev", "test", "staging", "prod"))
        parser.add_argument(
            "--directory", help="可信部署适配 module:Class，构造函数接收 SessionProvider"
        )
        arguments = parser.parse_args()
        try:
            result = asyncio.run(cls.run(arguments))
        except KeyboardInterrupt:
            return 130
        except Exception as error:
            print(
                f"租户部署切换失败：{type(error).__name__}；封存与业务配置必须一致。",
                file=sys.stderr,
            )
            return 1
        print(json.dumps(result))
        return 0

    @staticmethod
    async def run(arguments):
        current = ConfigProvider(
            BootstrapConfigProvider.load(arguments.config_dir, app_env=arguments.env),
            (DatabaseSettings, TenantSettings),
        )
        desired = ConfigProvider(
            BootstrapConfigProvider.load(arguments.target_config_dir, app_env=arguments.env),
            (TenantSettings,),
        )
        try:
            settings = current.get_config(DatabaseSettings)
            before = current.get_config(TenantSettings)
            after = desired.get_config(TenantSettings)
        finally:
            current.close()
            desired.close()
        database = SessionProvider(settings)
        try:
            await database.open()
            directory = None
            if arguments.directory is not None:
                module, separator, name = arguments.directory.partition(":")
                if not separator:
                    raise ValueError("directory 使用 module:Class")
                directory = getattr(importlib.import_module(module), name)(database)
            with database.scope():
                await DeploymentModeStore(database, before).transition(after, directory)
        finally:
            await database.close()
        return {"enabled": after.enabled, "profile": after.profile.value, "restart_required": True}
