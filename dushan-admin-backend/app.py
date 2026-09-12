import os
import subprocess
import sys
from pathlib import Path

# 先关掉字节码写入，再导入项目模块，避免生成 __pycache__。
sys.dont_write_bytecode = True

from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_web.banner.banner_application_runner import BannerApplicationRunner
from server.config.application_settings import ApplicationSettings
from server.enums.server_engine_enum import ServerEngineEnum
from server.launcher.engine_parser import parse_server_arguments
from server.launcher.granian_launcher import build_granian_cmd
from server.launcher.uvicorn_launcher import build_uvicorn_cmd

BACKEND_ROOT = Path(__file__).resolve().parent


def run_server(argv=None) -> int:
    """检查启动配置，启动服务器并返回退出码。"""
    args = parse_server_arguments(argv)
    try:
        config_dir = args.config_dir if args.config_dir is not None else BACKEND_ROOT
        provider = BootstrapConfigProvider.load(config_dir, app_env=args.env)
        configuration = provider.get_config(ApplicationSettings)
        settings = configuration.server
        engine = args.server if args.server is not None else settings.engine
        BannerApplicationRunner(configuration.banner).print_startup_banner()
        if engine is ServerEngineEnum.GRANIAN:
            command = build_granian_cmd(settings, configuration.granian)
        else:
            command = build_uvicorn_cmd(settings, configuration.uvicorn)
    except BootstrapConfigError as error:
        print(f"启动配置错误：{error}", file=sys.stderr)
        return 2

    # 移除引擎自己读取的环境变量，保证子进程使用刚校验过的启动参数。
    child_env = {
        key: value
        for key, value in os.environ.items()
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
        result = subprocess.run(command, cwd=BACKEND_ROOT, env=child_env, check=False)
        if result.returncode:
            print(f"服务进程异常退出，退出码：{result.returncode}", file=sys.stderr)
        return result.returncode
    except OSError:
        print("无法启动服务进程，请检查 Python 环境与依赖安装。", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("服务已停止。")
        return 130


if __name__ == "__main__":
    raise SystemExit(run_server())
