"""渡山后端统一命令行启动入口。"""

import os
import subprocess
import sys
from pathlib import Path

# 启动入口不在源码目录生成 Python 字节码。
sys.dont_write_bytecode = True

from framework.starter_config.provider.bootstrap_config_provider import (
    BootstrapConfigError,
    BootstrapConfigProvider,
)
from server.config.application_settings import ApplicationSettings
from server.launcher.engine_parser import parse_server_arguments
from server.launcher.granian_launcher import build_granian_cmd
from server.launcher.uvicorn_launcher import build_uvicorn_cmd

BACKEND_ROOT = Path(__file__).resolve().parent


def run_server(argv=None) -> int:
    """先完成配置校验，再以参数列表启动服务器进程。"""
    args = parse_server_arguments(argv)
    try:
        provider = BootstrapConfigProvider.load(args.config_dir or BACKEND_ROOT, app_env=args.env)
        configuration = provider.get_config(ApplicationSettings)
        settings = configuration.server
        if args.server == "granian":
            command = build_granian_cmd(settings, configuration.granian)
        else:
            command = build_uvicorn_cmd(settings, configuration.uvicorn)
    except BootstrapConfigError as error:
        print(f"启动配置错误：{error}", file=sys.stderr)
        return 2

    # 引擎参数已经显式传入，清除引擎自身的环境覆盖，防止绕过已验证参数。
    child_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("UVICORN_", "GRANIAN_"))
    }
    child_env.update(
        {
            "SERVER_ENV": settings.env.value,
            "DUSHAN_CONFIG_DIR": str(provider.base_dir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    print(
        f"启动 {settings.name}，引擎：{args.server}，环境：{settings.env.value}",
        flush=True,
    )
    print(f"监听地址：http://{settings.host}:{settings.port}", flush=True)
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
