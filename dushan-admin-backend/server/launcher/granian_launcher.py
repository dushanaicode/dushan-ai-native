import sys

from server.config.granian.granian_settings import GranianSettings
from server.config.server.server_settings import ServerSettings
from server.launcher.worker_count_guard import resolve_effective_worker_count


def build_granian_cmd(server: ServerSettings, engine: GranianSettings) -> list[str]:
    """根据服务配置生成 Granian 启动命令。"""
    command = [
        sys.executable,
        "-B",
        "-m",
        "granian",
        "--interface",
        "asgi",
        "--no-access-log",
        "server.starter_server:app",
        "--host",
        server.host,
        "--port",
        str(server.port),
        "--workers",
        str(resolve_effective_worker_count(engine.workers, server.reload)),
    ]
    if server.reload:
        command += [
            "--reload",
            "--reload-ignore-dirs",
            "Temp",
            "--reload-ignore-dirs",
            ".venv",
        ]
    else:
        command += ["--runtime-threads", str(engine.threads)]
    return command
