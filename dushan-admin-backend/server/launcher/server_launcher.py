import os
import subprocess
import sys
from pathlib import Path

from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_web.banner.banner_application_runner import BannerApplicationRunner
from server.config.application_settings import ApplicationSettings
from server.enums.server_engine_enum import ServerEngineEnum
from server.launcher.engine_parser import EngineParser
from server.launcher.granian_launcher import GranianLauncher
from server.launcher.uvicorn_launcher import UvicornLauncher


class ServerLauncher:
    BACKEND_ROOT = Path(__file__).resolve().parents[2]

    @staticmethod
    def run(argv=None) -> int:
        """检查启动配置，启动服务器并返回退出码。"""
        args = EngineParser.parse(argv)
        try:
            config_dir = (
                args.config_dir if args.config_dir is not None else ServerLauncher.BACKEND_ROOT
            )
            process_env = dict(os.environ)
            provider = BootstrapConfigProvider.load(
                config_dir, app_env=args.env, environ=process_env
            )
            configuration = provider.get_config(ApplicationSettings)
            settings = configuration.server
            engine = args.server if args.server is not None else settings.engine
            BannerApplicationRunner(configuration.banner).print_startup_banner()
            if engine is ServerEngineEnum.GRANIAN:
                command = GranianLauncher.build_command(settings, configuration.granian)
            else:
                command = UvicornLauncher.build_command(settings, configuration.uvicorn)
        except BootstrapConfigError as error:
            print(f"启动配置错误：{error}", file=sys.stderr)
            return 2

        # 移除引擎自己读取的环境变量，保证子进程使用刚校验过的启动参数。
        child_env = {
            key: value
            for key, value in process_env.items()
            if not key.startswith(("UVICORN_", "GRANIAN_"))
        }
        child_env.update(
            {
                "SERVER_ENV": settings.env.value,
                "SERVER_ENGINE": engine.value,
                "DUSHAN_CONFIG_DIR": str(provider.base_dir),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        try:
            result = subprocess.run(
                command, cwd=ServerLauncher.BACKEND_ROOT, env=child_env, check=False
            )
            if result.returncode:
                print(f"服务进程异常退出，退出码：{result.returncode}", file=sys.stderr)
            return result.returncode
        except OSError:
            print("无法启动服务进程，请检查 Python 环境与依赖安装。", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("服务已停止。")
            return 130
